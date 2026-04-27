"""Calendar endpoints — list scheduled posts in a window + drag-to-reschedule."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.scheduled_post import (
    STATUS_PENDING_APPROVAL,
    STATUS_SCHEDULED,
    ScheduledPostModel,
)
from app.routers.publish.schemas import DraftResponse, RescheduleRequest

router = APIRouter(prefix="/publish/calendar", tags=["Publish - Calendar"])


@router.get("", response_model=list[DraftResponse])
async def list_calendar(
    brand=Depends(require_brand),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    statuses: str | None = Query(None, description="Comma-separated subset"),
) -> Any:
    """List scheduled / pending posts whose ``scheduled_at`` falls inside the window."""
    db = get_session_local()()
    try:
        wanted_statuses = (
            [s.strip() for s in statuses.split(",")] if statuses
            else None
        )
        q = db.query(ScheduledPostModel).filter(
            ScheduledPostModel.brand_id == brand.id,
            ScheduledPostModel.deleted_at.is_(None),
            ScheduledPostModel.scheduled_at.isnot(None),
            ScheduledPostModel.scheduled_at >= from_,
            ScheduledPostModel.scheduled_at <= to,
        )
        if wanted_statuses:
            q = q.filter(ScheduledPostModel.status.in_(wanted_statuses))
        return q.order_by(ScheduledPostModel.scheduled_at.asc()).all()
    finally:
        db.close()


@router.patch("/{draft_id}/reschedule", response_model=DraftResponse)
async def reschedule(
    draft_id: int,
    payload: RescheduleRequest,
    brand=Depends(require_brand),
) -> Any:
    """Drag-to-reschedule. Only valid for posts not yet picked up by the publisher."""
    db = get_session_local()()
    try:
        post = (
            db.query(ScheduledPostModel)
            .filter(
                ScheduledPostModel.id == draft_id,
                ScheduledPostModel.brand_id == brand.id,
                ScheduledPostModel.deleted_at.is_(None),
            )
            .first()
        )
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        if post.status not in (STATUS_SCHEDULED, STATUS_PENDING_APPROVAL):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reschedule post in status '{post.status}'",
            )
        post.scheduled_at = payload.scheduled_at
        db.commit()
        db.refresh(post)
        return post
    finally:
        db.close()
