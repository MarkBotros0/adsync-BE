"""Composer endpoints — draft CRUD + approval workflow.

Lifecycle:
    draft → pending_approval → scheduled → publishing → published | failed
ORG_ADMIN authors can skip ``pending_approval`` and submit straight to ``scheduled``.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.scheduled_post import (
    STATUS_DRAFT,
    STATUS_FAILED,
    STATUS_PENDING_APPROVAL,
    STATUS_PUBLISHED,
    STATUS_PUBLISHING,
    STATUS_SCHEDULED,
    ScheduledPostModel,
)
from app.repositories.organization_membership import OrganizationMembershipRepository
from app.routers.publish.schemas import (
    DraftCreate,
    DraftResponse,
    DraftUpdate,
    RejectRequest,
)

router = APIRouter(prefix="/publish/drafts", tags=["Publish - Composer"])
logger = logging.getLogger(__name__)


def _get_draft(db: Session, draft_id: int, brand_id: int) -> ScheduledPostModel:
    obj = (
        db.query(ScheduledPostModel)
        .filter(
            ScheduledPostModel.id == draft_id,
            ScheduledPostModel.brand_id == brand_id,
            ScheduledPostModel.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Draft not found")
    return obj


def _is_org_admin(db: Session, user_id: int, organization_id: int | None) -> bool:
    """ORG_ADMIN gets to skip approval. SUPER (id=0) always counts as admin."""
    if user_id == 0:
        return True
    if organization_id is None:
        return False
    membership = OrganizationMembershipRepository(db).get_membership(
        user_id=user_id, org_id=organization_id,
    )
    return bool(membership and membership.role == "ORG_ADMIN")


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DraftResponse])
async def list_drafts(
    brand=Depends(require_brand),
    status_filter: str | None = None,
) -> Any:
    """List all drafts/scheduled/published posts for the brand. Optional ``status_filter``."""
    db = get_session_local()()
    try:
        q = db.query(ScheduledPostModel).filter(
            ScheduledPostModel.brand_id == brand.id,
            ScheduledPostModel.deleted_at.is_(None),
        )
        if status_filter:
            q = q.filter(ScheduledPostModel.status == status_filter)
        return q.order_by(ScheduledPostModel.created_at.desc()).limit(500).all()
    finally:
        db.close()


@router.post("", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(payload: DraftCreate, brand=Depends(require_brand)) -> Any:
    """Create a draft. ``status`` is always ``draft`` here — submission is a separate call."""
    db = get_session_local()()
    try:
        # The brand object on require_brand has no user_id directly — it's a brand record.
        # The author is the user who owns the JWT; we recover it from request state.
        # Simpler: store the brand owner-id pattern used elsewhere (the brand's id stands in
        # for now since the multi-user model uses user_brands; we revisit when integrating
        # with the JWT user claim).
        author_user_id = getattr(brand, "owner_user_id", None) or 0
        draft = ScheduledPostModel(
            brand_id=brand.id,
            author_user_id=author_user_id,
            status=STATUS_DRAFT,
            scheduled_at=payload.scheduled_at,
            text=payload.text,
            platforms_json=[p.lower() for p in payload.platforms],
            per_platform_payload_json=payload.per_platform_payload or {},
            media_asset_ids_json=payload.media_asset_ids or [],
            campaign_tag_ids_json=payload.campaign_tag_ids or [],
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()


@router.patch("/{draft_id}", response_model=DraftResponse)
async def update_draft(
    draft_id: int,
    payload: DraftUpdate,
    brand=Depends(require_brand),
) -> Any:
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status not in (STATUS_DRAFT, STATUS_PENDING_APPROVAL):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot edit a draft in status '{draft.status}'",
            )
        if payload.text is not None:
            draft.text = payload.text
        if payload.platforms is not None:
            draft.platforms_json = [p.lower() for p in payload.platforms]
        if payload.per_platform_payload is not None:
            draft.per_platform_payload_json = payload.per_platform_payload
        if payload.media_asset_ids is not None:
            draft.media_asset_ids_json = payload.media_asset_ids
        if payload.campaign_tag_ids is not None:
            draft.campaign_tag_ids_json = payload.campaign_tag_ids
        if payload.scheduled_at is not None:
            draft.scheduled_at = payload.scheduled_at
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(draft_id: int, brand=Depends(require_brand)) -> None:
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status in (STATUS_PUBLISHING, STATUS_PUBLISHED):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete a draft in status '{draft.status}'",
            )
        draft.deleted_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


# ── Approval workflow ──────────────────────────────────────────────────────

@router.post("/{draft_id}/submit", response_model=DraftResponse)
async def submit_for_approval(draft_id: int, brand=Depends(require_brand)) -> Any:
    """Submit a draft for ORG_ADMIN approval.

    If the author IS already an ORG_ADMIN, the draft skips ``pending_approval`` and
    goes straight to ``scheduled`` (provided ``scheduled_at`` is set).
    """
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status != STATUS_DRAFT:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot submit a draft in status '{draft.status}'",
            )
        if not draft.platforms_json:
            raise HTTPException(status_code=422, detail="At least one platform is required")
        is_admin = _is_org_admin(db, draft.author_user_id, brand.organization_id)
        if is_admin:
            if not draft.scheduled_at:
                raise HTTPException(
                    status_code=422,
                    detail="scheduled_at is required when bypassing approval",
                )
            draft.status = STATUS_SCHEDULED
            draft.approval_user_id = draft.author_user_id
            draft.approved_at = datetime.utcnow()
        else:
            draft.status = STATUS_PENDING_APPROVAL
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()


@router.post("/{draft_id}/approve", response_model=DraftResponse)
async def approve_draft(draft_id: int, brand=Depends(require_brand)) -> Any:
    """Approve a pending draft (ORG_ADMIN only)."""
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status != STATUS_PENDING_APPROVAL:
            raise HTTPException(
                status_code=409,
                detail=f"Draft is not awaiting approval (status='{draft.status}')",
            )
        # Brand-level role check — full per-user check happens in /v2 later.
        if not _is_org_admin(db, getattr(brand, "owner_user_id", 0), brand.organization_id):
            raise HTTPException(status_code=403, detail="Only ORG_ADMIN can approve drafts")
        if not draft.scheduled_at:
            raise HTTPException(
                status_code=422,
                detail="scheduled_at must be set on the draft before approval",
            )
        draft.status = STATUS_SCHEDULED
        draft.approval_user_id = getattr(brand, "owner_user_id", 0)
        draft.approved_at = datetime.utcnow()
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()


@router.post("/{draft_id}/reject", response_model=DraftResponse)
async def reject_draft(
    draft_id: int,
    payload: RejectRequest,
    brand=Depends(require_brand),
) -> Any:
    """Reject a pending draft and return it to ``draft`` with a stored reason (ORG_ADMIN only)."""
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status != STATUS_PENDING_APPROVAL:
            raise HTTPException(
                status_code=409,
                detail=f"Draft is not awaiting approval (status='{draft.status}')",
            )
        if not _is_org_admin(db, getattr(brand, "owner_user_id", 0), brand.organization_id):
            raise HTTPException(status_code=403, detail="Only ORG_ADMIN can reject drafts")
        draft.status = STATUS_DRAFT
        draft.rejection_reason = payload.reason
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()


@router.post("/{draft_id}/cancel", response_model=DraftResponse)
async def cancel_scheduled(draft_id: int, brand=Depends(require_brand)) -> Any:
    """Pull a scheduled post back into draft (only valid before publishing starts)."""
    db = get_session_local()()
    try:
        draft = _get_draft(db, draft_id, brand.id)
        if draft.status != STATUS_SCHEDULED:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel a draft in status '{draft.status}'",
            )
        draft.status = STATUS_DRAFT
        draft.approval_user_id = None
        draft.approved_at = None
        db.commit()
        db.refresh(draft)
        return draft
    finally:
        db.close()
