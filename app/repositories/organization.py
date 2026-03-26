from datetime import datetime
from sqlalchemy.orm import Session
from app.models.organization import OrganizationModel
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[OrganizationModel]):
    """Repository for organization operations."""

    def __init__(self, db: Session):
        super().__init__(OrganizationModel, db)

    def get_by_id(self, org_id: int) -> OrganizationModel | None:
        return self.get(org_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[OrganizationModel]:
        return (
            self.db.query(OrganizationModel)
            .filter(OrganizationModel.deleted_at.is_(None))
            .order_by(OrganizationModel.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_organization(
        self,
        name: str,
        subscription_id: int | None = None,
        logo_url: str | None = None,
    ) -> OrganizationModel:
        org = OrganizationModel(
            name=name,
            subscription_id=subscription_id,
            logo_url=logo_url,
        )
        return self.create(org)

    def count_active_brands(self, org_id: int) -> int:
        from app.models.brand import BrandModel
        return (
            self.db.query(BrandModel)
            .filter(
                BrandModel.organization_id == org_id,
                BrandModel.is_active.is_(True),
                BrandModel.deleted_at.is_(None),
            )
            .count()
        )

    def update_subscription(self, org: OrganizationModel, subscription_id: int) -> OrganizationModel:
        org.subscription_id = subscription_id
        org.updated_at = datetime.utcnow()
        return self.update(org)
