"""Pydantic schemas shared across the publish routers (composer, calendar, media)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DraftCreate(BaseModel):
    text: str = Field("", max_length=4000)
    platforms: list[str] = Field(default_factory=list, description="facebook | instagram | tiktok")
    per_platform_payload: dict[str, dict[str, Any]] = Field(default_factory=dict)
    media_asset_ids: list[int] = Field(default_factory=list)
    campaign_tag_ids: list[int] = Field(default_factory=list)
    scheduled_at: datetime | None = None


class DraftUpdate(BaseModel):
    text: str | None = Field(None, max_length=4000)
    platforms: list[str] | None = None
    per_platform_payload: dict[str, dict[str, Any]] | None = None
    media_asset_ids: list[int] | None = None
    campaign_tag_ids: list[int] | None = None
    scheduled_at: datetime | None = None


class DraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    author_user_id: int
    status: str
    scheduled_at: datetime | None = None
    text: str
    platforms_json: list[str]
    per_platform_payload_json: dict[str, dict[str, Any]]
    media_asset_ids_json: list[int]
    campaign_tag_ids_json: list[int]
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    published_at: datetime | None = None
    platform_post_ids_json: dict[str, str] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=400)


class RescheduleRequest(BaseModel):
    scheduled_at: datetime


class MediaAssetSummary(BaseModel):
    """List view — never includes ``content`` bytes."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    kind: str
    filename: str
    mime: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    created_at: datetime
