from datetime import datetime
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
        subscription_id: int | None = None,
        logo_url: str | None = None,
        website: str | None = None,
        industry: str | None = None,
    ) -> BrandModel:
        brand = BrandModel(
            name=name,
            subscription_id=subscription_id,
            logo_url=logo_url,
            website=website,
            industry=industry,
        )
        return self.create(brand)

    def update_subscription(self, brand: BrandModel, subscription_id: int) -> BrandModel:
        brand.subscription_id = subscription_id
        brand.updated_at = datetime.utcnow()
        return self.update(brand)
