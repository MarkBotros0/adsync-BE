from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.subscription import SubscriptionModel, DEFAULT_SUBSCRIPTIONS
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[SubscriptionModel]):
    """Repository for subscription plan operations"""

    def __init__(self, db: Session):
        super().__init__(SubscriptionModel, db)

    def get_by_name(self, name: str) -> Optional[SubscriptionModel]:
        return self.get_by_field(name=name)

    def get_active(self) -> List[SubscriptionModel]:
        return self.db.query(SubscriptionModel).filter(
            SubscriptionModel.is_active == True  # noqa: E712
        ).all()

    def seed_defaults(self) -> None:
        """Insert default plans if they don't already exist."""
        for plan in DEFAULT_SUBSCRIPTIONS:
            existing = self.get_by_name(plan["name"])
            if not existing:
                obj = SubscriptionModel(**plan)
                self.db.add(obj)
        self.db.commit()
