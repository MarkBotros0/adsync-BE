"""Scheduled (or draft / pending-approval) post awaiting publish to one or more platforms."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


# Status lifecycle for a draft post.
STATUS_DRAFT = "draft"                       # author still editing
STATUS_PENDING_APPROVAL = "pending_approval" # waiting for ORG_ADMIN approval
STATUS_SCHEDULED = "scheduled"               # approved, awaiting scheduled_at
STATUS_PUBLISHING = "publishing"             # publisher loop has picked it up
STATUS_PUBLISHED = "published"               # successfully posted to all platforms
STATUS_FAILED = "failed"                     # all retries exhausted

ALL_STATUSES = (
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_SCHEDULED,
    STATUS_PUBLISHING,
    STATUS_PUBLISHED,
    STATUS_FAILED,
)


class ScheduledPostModel(Base):
    """A post that lives in OUR DB before being pushed to one or more platforms.

    ``platforms_json`` is the list of platforms the user wants to publish to
    (``["facebook", "instagram", "tiktok"]``).
    ``per_platform_payload_json`` lets the user override caption/hashtags per platform
    (because IG captions differ in style from FB ones); shape is
    ``{ "facebook": {"text": "..."}, "instagram": {"text": "..."} }``.
    ``platform_post_ids_json`` is filled in by the publisher loop on success:
    ``{ "facebook": "123_456", "instagram": "789..." }``.
    """

    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String, nullable=False, default=STATUS_DRAFT, index=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)

    text = Column(Text, nullable=False, default="")  # default caption
    platforms_json = Column(JSONB, nullable=False, default=list)
    per_platform_payload_json = Column(JSONB, nullable=False, default=dict)
    media_asset_ids_json = Column(JSONB, nullable=False, default=list)
    campaign_tag_ids_json = Column(JSONB, nullable=False, default=list)

    approval_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    published_at = Column(DateTime, nullable=True)
    platform_post_ids_json = Column(JSONB, nullable=True)

    attempt_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
