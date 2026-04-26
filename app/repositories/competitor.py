from datetime import datetime
import re

from sqlalchemy.orm import Session

from app.models.competitor import CompetitorModel
from app.repositories.base import BaseRepository


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_slug(name: str) -> str:
    """Normalize a brand name into a stable slug for dedupe within a brand."""
    return _SLUG_RE.sub("-", name.strip().lower()).strip("-")


class CompetitorRepository(BaseRepository[CompetitorModel]):
    def __init__(self, db: Session):
        super().__init__(CompetitorModel, db)

    def list_by_brand(self, brand_id: int) -> list[CompetitorModel]:
        return (
            self.db.query(CompetitorModel)
            .filter(
                CompetitorModel.brand_id == brand_id,
                CompetitorModel.deleted_at.is_(None),
            )
            .order_by(CompetitorModel.created_at.desc())
            .all()
        )

    def get_for_brand(self, brand_id: int, competitor_id: int) -> CompetitorModel | None:
        return (
            self.db.query(CompetitorModel)
            .filter(
                CompetitorModel.id == competitor_id,
                CompetitorModel.brand_id == brand_id,
                CompetitorModel.deleted_at.is_(None),
            )
            .first()
        )

    def find_by_slug(self, brand_id: int, slug: str) -> CompetitorModel | None:
        return (
            self.db.query(CompetitorModel)
            .filter(
                CompetitorModel.brand_id == brand_id,
                CompetitorModel.slug == slug,
                CompetitorModel.deleted_at.is_(None),
            )
            .first()
        )

    def create_for_brand(self, brand_id: int, name: str) -> CompetitorModel:
        competitor = CompetitorModel(
            brand_id=brand_id,
            name=name.strip(),
            slug=normalize_slug(name),
        )
        return self.create(competitor)

    def soft_delete_for_brand(self, brand_id: int, competitor_id: int) -> bool:
        competitor = self.get_for_brand(brand_id, competitor_id)
        if not competitor:
            return False
        now = datetime.utcnow()
        competitor.deleted_at = now
        competitor.updated_at = now
        self.db.commit()
        return True
