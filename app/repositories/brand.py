from sqlalchemy.orm import Session
from app.models.brand import BrandModel
from app.repositories.base import BaseRepository


class BrandRepository(BaseRepository[BrandModel]):
    """Repository for brand operations."""

    def __init__(self, db: Session):
        super().__init__(BrandModel, db)

    def get_by_id(self, brand_id: int) -> BrandModel | None:
        return self.get(brand_id)

    def get_all_brands(self, skip: int = 0, limit: int = 100) -> list[BrandModel]:
        return self.get_all(skip=skip, limit=limit)

    def create_brand(
        self,
        name: str,
        organization_id: int | None = None,
        logo_url: str | None = None,
        website: str | None = None,
        industry: str | None = None,
    ) -> BrandModel:
        brand = BrandModel(
            name=name,
            organization_id=organization_id,
            logo_url=logo_url,
            website=website,
            industry=industry,
        )
        return self.create(brand)

    def get_brands_for_org(self, org_id: int) -> list[BrandModel]:
        return (
            self.db.query(BrandModel)
            .filter(
                BrandModel.organization_id == org_id,
                BrandModel.deleted_at.is_(None),
            )
            .order_by(BrandModel.created_at)
            .all()
        )


