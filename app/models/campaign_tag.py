"""Campaign tag — brand-scoped label for grouping post performance.

A tag is a name + display colour. It can be attached to ingested posts (mentions from
the platform feeds) AND to scheduled posts the brand creates via the composer. Posts
↔ tags is many-to-many through the ``post_campaign_tags`` link table — kept simple by
storing the platform + post_id as a (string, string) pair so the same table works for
every platform without an FK explosion.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class CampaignTagModel(Base):
    """Brand-scoped tag for grouping posts under a campaign label (e.g. 'Q2 Launch')."""

    __tablename__ = "campaign_tags"
    __table_args__ = (
        UniqueConstraint("brand_id", "slug", name="uq_campaign_tags_brand_slug"),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    color = Column(String, nullable=False, default="#6366f1")  # default indigo
    description = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)


class PostCampaignTagModel(Base):
    """Many-to-many link between a (platform, post_id) and a CampaignTag.

    The post side is intentionally NOT an FK — posts on the platform feeds aren't
    rows in our DB, and scheduled posts have their own primary key. Storing
    ``platform`` + ``post_id`` as strings lets the same table cover both worlds
    without conditional FKs or polymorphic inheritance.
    """

    __tablename__ = "post_campaign_tags"
    __table_args__ = (
        UniqueConstraint(
            "brand_id", "platform", "post_id", "tag_id",
            name="uq_post_campaign_tags_brand_platform_post_tag",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    tag_id = Column(Integer, ForeignKey("campaign_tags.id"), index=True, nullable=False)

    platform = Column(String, nullable=False, index=True)  # facebook | instagram | tiktok
    post_id = Column(String, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
