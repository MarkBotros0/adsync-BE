import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.brand import BrandModel
from app.repositories.base import BaseRepository


class BrandRepository(BaseRepository[BrandModel]):
    """Repository for brand account operations"""

    def __init__(self, db: Session):
        super().__init__(BrandModel, db)

    def get_by_email(self, email: str) -> Optional[BrandModel]:
        return self.get_by_field(email=email)

    def get_by_id(self, brand_id: int) -> Optional[BrandModel]:
        return self.get(brand_id)

    def create_brand(
        self,
        name: str,
        email: str,
        hashed_password: str,
        subscription_id: Optional[int] = None,
        logo_url: Optional[str] = None,
        website: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> BrandModel:
        brand = BrandModel(
            name=name,
            email=email,
            hashed_password=hashed_password,
            subscription_id=subscription_id,
            logo_url=logo_url,
            website=website,
            industry=industry,
            session_key=str(uuid.uuid4()),
        )
        return self.create(brand)

    def rotate_session_key(self, brand: BrandModel) -> BrandModel:
        """Invalidate all existing JWTs by rotating the session key."""
        brand.session_key = str(uuid.uuid4())
        brand.updated_at = datetime.utcnow()
        return self.update(brand)

    def update_subscription(self, brand: BrandModel, subscription_id: int) -> BrandModel:
        brand.subscription_id = subscription_id
        brand.updated_at = datetime.utcnow()
        return self.update(brand)

    def set_verification_code(self, brand: BrandModel, code: str, expires_at: datetime) -> BrandModel:
        brand.email_verification_code = code
        brand.email_verification_expires_at = expires_at
        brand.updated_at = datetime.utcnow()
        return self.update(brand)

    def mark_email_verified(self, brand: BrandModel) -> BrandModel:
        brand.is_email_verified = True
        brand.email_verification_code = None
        brand.email_verification_expires_at = None
        brand.updated_at = datetime.utcnow()
        return self.update(brand)

    def deactivate(self, brand: BrandModel) -> BrandModel:
        brand.is_active = False
        brand.updated_at = datetime.utcnow()
        return self.update(brand)
