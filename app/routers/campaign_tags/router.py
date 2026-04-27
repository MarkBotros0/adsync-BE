"""Campaign tag CRUD + post attachment endpoints — brand-JWT authenticated."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.campaign_tag import (
    CampaignTagRepository,
    PostCampaignTagRepository,
    slugify,
)


router = APIRouter(prefix="/campaign-tags", tags=["Campaign Tags"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class CampaignTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = Field(None, max_length=200)


class CampaignTagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = Field(None, max_length=200)


class CampaignTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    name: str
    slug: str
    color: str
    description: str | None = None


class PostTagAttachRequest(BaseModel):
    platform: str = Field(..., description="facebook | instagram | tiktok")
    post_id: str
    tag_ids: list[int] = Field(default_factory=list)


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CampaignTagResponse])
async def list_tags(brand=Depends(require_brand)) -> Any:
    """List all campaign tags for the current brand."""
    db = get_session_local()()
    try:
        return CampaignTagRepository(db).list_for_brand(brand.id)
    finally:
        db.close()


@router.post("", response_model=CampaignTagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: CampaignTagCreate,
    brand=Depends(require_brand),
) -> Any:
    """Create a campaign tag for the current brand. Slug is derived from name."""
    db = get_session_local()()
    try:
        repo = CampaignTagRepository(db)
        if repo.get_by_slug(brand.id, slugify(payload.name)):
            raise HTTPException(status_code=409, detail="A tag with this name already exists")
        return repo.create_tag(
            brand_id=brand.id,
            name=payload.name,
            color=payload.color,
            description=payload.description,
        )
    finally:
        db.close()


@router.patch("/{tag_id}", response_model=CampaignTagResponse)
async def update_tag(
    tag_id: int,
    payload: CampaignTagUpdate,
    brand=Depends(require_brand),
) -> Any:
    db = get_session_local()()
    try:
        repo = CampaignTagRepository(db)
        tag = repo.get_for_brand(brand.id, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        if payload.name is not None:
            tag.name = payload.name.strip()
            tag.slug = slugify(payload.name)
        if payload.color is not None:
            tag.color = payload.color
        if payload.description is not None:
            tag.description = payload.description
        return repo.update(tag)
    finally:
        db.close()


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, brand=Depends(require_brand)) -> None:
    """Soft-delete the tag. Existing post links remain in the DB but stop appearing."""
    db = get_session_local()()
    try:
        repo = CampaignTagRepository(db)
        if not repo.get_for_brand(brand.id, tag_id):
            raise HTTPException(status_code=404, detail="Tag not found")
        repo.soft_delete(tag_id)
    finally:
        db.close()


# ── Post ↔ tag attachment ────────────────────────────────────────────────────

@router.post("/posts/attach", status_code=status.HTTP_200_OK)
async def attach_tags_to_post(
    payload: PostTagAttachRequest,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Attach one or more tags to a (platform, post_id) — idempotent.

    Replaces the post's tag set with exactly ``tag_ids``: any current tag not in the
    list is detached, any new one is attached. This is the simplest contract for the
    composer / content row picker — the FE sends what it wants, server reconciles.
    """
    db = get_session_local()()
    try:
        tag_repo = CampaignTagRepository(db)
        link_repo = PostCampaignTagRepository(db)

        # Validate every tag belongs to this brand before mutating anything.
        valid: list[int] = []
        for tid in payload.tag_ids:
            if tag_repo.get_for_brand(brand.id, tid):
                valid.append(tid)

        current = set(link_repo.tags_for_post(brand.id, payload.platform, payload.post_id))
        wanted = set(valid)

        for tid in current - wanted:
            link_repo.detach(brand.id, tid, payload.platform, payload.post_id)
        for tid in wanted - current:
            link_repo.attach(brand.id, tid, payload.platform, payload.post_id)

        return {
            "success": True,
            "data": {
                "platform": payload.platform,
                "post_id": payload.post_id,
                "tag_ids": sorted(wanted),
            },
        }
    finally:
        db.close()


@router.get("/posts/lookup")
async def lookup_post_tags(
    platform: str,
    post_id: str,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Return the tag IDs currently attached to a single post."""
    db = get_session_local()()
    try:
        link_repo = PostCampaignTagRepository(db)
        return {
            "success": True,
            "data": {
                "platform": platform,
                "post_id": post_id,
                "tag_ids": link_repo.tags_for_post(brand.id, platform, post_id),
            },
        }
    finally:
        db.close()
