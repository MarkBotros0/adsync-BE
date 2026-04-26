from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.competitor_target import CompetitorTargetModel
from app.repositories.base import BaseRepository


class CompetitorTargetRepository(BaseRepository[CompetitorTargetModel]):
    def __init__(self, db: Session):
        super().__init__(CompetitorTargetModel, db)

    def list_for_competitor(self, competitor_id: int) -> list[CompetitorTargetModel]:
        return (
            self.db.query(CompetitorTargetModel)
            .filter(
                CompetitorTargetModel.competitor_id == competitor_id,
                CompetitorTargetModel.deleted_at.is_(None),
            )
            .order_by(CompetitorTargetModel.actor_key.asc())
            .all()
        )

    def get_for_competitor(
        self,
        competitor_id: int,
        actor_key: str,
    ) -> CompetitorTargetModel | None:
        return (
            self.db.query(CompetitorTargetModel)
            .filter(
                CompetitorTargetModel.competitor_id == competitor_id,
                CompetitorTargetModel.actor_key == actor_key,
                CompetitorTargetModel.deleted_at.is_(None),
            )
            .first()
        )

    def upsert(
        self,
        *,
        brand_id: int,
        competitor_id: int,
        actor_key: str,
        target_value: str,
        target_type: str,
        is_enabled: bool = True,
    ) -> CompetitorTargetModel:
        existing = self.get_for_competitor(competitor_id, actor_key)
        if existing:
            existing.target_value = target_value
            existing.target_type = target_type
            existing.is_enabled = is_enabled
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        target = CompetitorTargetModel(
            brand_id=brand_id,
            competitor_id=competitor_id,
            actor_key=actor_key,
            target_value=target_value,
            target_type=target_type,
            is_enabled=is_enabled,
        )
        return self.create(target)

    def soft_delete_for_competitor(
        self,
        competitor_id: int,
        actor_key: str,
    ) -> bool:
        target = self.get_for_competitor(competitor_id, actor_key)
        if not target:
            return False
        now = datetime.utcnow()
        target.deleted_at = now
        target.updated_at = now
        self.db.commit()
        return True

    def mark_run(
        self,
        target_id: int,
        cost_usd: Decimal | float | None,
    ) -> None:
        target = self.get(target_id)
        if not target:
            return
        now = datetime.utcnow()
        target.last_run_at = now
        if cost_usd is not None:
            target.last_cost_usd = Decimal(str(cost_usd))
        target.updated_at = now
        self.db.commit()
