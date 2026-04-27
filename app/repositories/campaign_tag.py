"""Repositories for campaign tags + post-tag links."""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.campaign_tag import CampaignTagModel, PostCampaignTagModel
from app.repositories.base import BaseRepository


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Convert a tag display name to a URL-safe slug used for the brand-unique key."""
    s = _SLUG_RE.sub("-", (name or "").strip().lower()).strip("-")
    return s or "tag"


class CampaignTagRepository(BaseRepository[CampaignTagModel]):
    """CRUD for ``CampaignTagModel`` scoped to a single brand."""

    def __init__(self, db: Session) -> None:
        super().__init__(CampaignTagModel, db)

    def list_for_brand(self, brand_id: int) -> list[CampaignTagModel]:
        return (
            self.db.query(CampaignTagModel)
            .filter(
                CampaignTagModel.brand_id == brand_id,
                CampaignTagModel.deleted_at.is_(None),
            )
            .order_by(CampaignTagModel.name.asc())
            .all()
        )

    def get_for_brand(self, brand_id: int, tag_id: int) -> CampaignTagModel | None:
        return (
            self.db.query(CampaignTagModel)
            .filter(
                CampaignTagModel.id == tag_id,
                CampaignTagModel.brand_id == brand_id,
                CampaignTagModel.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_slug(self, brand_id: int, slug: str) -> CampaignTagModel | None:
        return (
            self.db.query(CampaignTagModel)
            .filter(
                CampaignTagModel.brand_id == brand_id,
                CampaignTagModel.slug == slug,
                CampaignTagModel.deleted_at.is_(None),
            )
            .first()
        )

    def create_tag(
        self,
        brand_id: int,
        name: str,
        color: str | None = None,
        description: str | None = None,
    ) -> CampaignTagModel:
        tag = CampaignTagModel(
            brand_id=brand_id,
            name=name.strip(),
            slug=slugify(name),
            color=color or "#6366f1",
            description=description,
        )
        return self.create(tag)


class PostCampaignTagRepository(BaseRepository[PostCampaignTagModel]):
    """Manage the many-to-many between posts and campaign tags."""

    def __init__(self, db: Session) -> None:
        super().__init__(PostCampaignTagModel, db)

    def attach(
        self,
        brand_id: int,
        tag_id: int,
        platform: str,
        post_id: str,
    ) -> PostCampaignTagModel:
        """Idempotent attach — re-attaching the same triple is a no-op (returns existing row)."""
        existing = self._get(brand_id, tag_id, platform, post_id)
        if existing:
            return existing
        link = PostCampaignTagModel(
            brand_id=brand_id, tag_id=tag_id, platform=platform.lower(), post_id=post_id,
        )
        return self.create(link)

    def detach(self, brand_id: int, tag_id: int, platform: str, post_id: str) -> bool:
        existing = self._get(brand_id, tag_id, platform, post_id)
        if not existing:
            return False
        existing.deleted_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def tags_for_post(self, brand_id: int, platform: str, post_id: str) -> list[int]:
        rows = (
            self.db.query(PostCampaignTagModel.tag_id)
            .filter(
                PostCampaignTagModel.brand_id == brand_id,
                PostCampaignTagModel.platform == platform.lower(),
                PostCampaignTagModel.post_id == post_id,
                PostCampaignTagModel.deleted_at.is_(None),
            )
            .all()
        )
        return [r[0] for r in rows]

    def tags_for_posts_bulk(
        self, brand_id: int, posts: list[tuple[str, str]]
    ) -> dict[tuple[str, str], list[int]]:
        """Bulk lookup: returns ``{(platform, post_id): [tag_id, ...]}`` for every (p,id) pair.

        Drives the /content feed page so attaching a column of tag chips is one query
        instead of N.
        """
        if not posts:
            return {}
        platforms = {p.lower() for p, _ in posts}
        post_ids = {pid for _, pid in posts}
        rows = (
            self.db.query(
                PostCampaignTagModel.platform,
                PostCampaignTagModel.post_id,
                PostCampaignTagModel.tag_id,
            )
            .filter(
                PostCampaignTagModel.brand_id == brand_id,
                PostCampaignTagModel.platform.in_(platforms),
                PostCampaignTagModel.post_id.in_(post_ids),
                PostCampaignTagModel.deleted_at.is_(None),
            )
            .all()
        )
        out: dict[tuple[str, str], list[int]] = {}
        for platform, post_id, tag_id in rows:
            out.setdefault((platform, post_id), []).append(tag_id)
        return out

    def posts_for_tag(self, brand_id: int, tag_id: int) -> list[tuple[str, str]]:
        rows = (
            self.db.query(PostCampaignTagModel.platform, PostCampaignTagModel.post_id)
            .filter(
                PostCampaignTagModel.brand_id == brand_id,
                PostCampaignTagModel.tag_id == tag_id,
                PostCampaignTagModel.deleted_at.is_(None),
            )
            .all()
        )
        return [(p, pid) for p, pid in rows]

    def _get(
        self, brand_id: int, tag_id: int, platform: str, post_id: str
    ) -> PostCampaignTagModel | None:
        return (
            self.db.query(PostCampaignTagModel)
            .filter(
                PostCampaignTagModel.brand_id == brand_id,
                PostCampaignTagModel.tag_id == tag_id,
                PostCampaignTagModel.platform == platform.lower(),
                PostCampaignTagModel.post_id == post_id,
                PostCampaignTagModel.deleted_at.is_(None),
            )
            .first()
        )
