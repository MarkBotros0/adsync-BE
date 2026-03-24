from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user_brand import UserBrandModel, BrandMembershipRole
from app.repositories.base import BaseRepository


class UserBrandRepository(BaseRepository[UserBrandModel]):
    """Repository for user-brand membership operations."""

    def __init__(self, db: Session):
        super().__init__(UserBrandModel, db)

    def create_membership(
        self,
        user_id: int,
        brand_id: int,
        role: BrandMembershipRole = BrandMembershipRole.NORMAL,
    ) -> UserBrandModel:
        membership = UserBrandModel(
            user_id=user_id,
            brand_id=brand_id,
            role=role,
        )
        return self.create(membership)

    def get_membership(self, user_id: int, brand_id: int) -> UserBrandModel | None:
        return (
            self.db.query(UserBrandModel)
            .filter(
                UserBrandModel.user_id == user_id,
                UserBrandModel.brand_id == brand_id,
                UserBrandModel.deleted_at.is_(None),
            )
            .first()
        )

    def get_brands_for_user(self, user_id: int) -> list[UserBrandModel]:
        return (
            self.db.query(UserBrandModel)
            .filter(
                UserBrandModel.user_id == user_id,
                UserBrandModel.deleted_at.is_(None),
            )
            .order_by(UserBrandModel.created_at)
            .all()
        )

    def get_users_for_brand(self, brand_id: int) -> list[UserBrandModel]:
        return (
            self.db.query(UserBrandModel)
            .filter(
                UserBrandModel.brand_id == brand_id,
                UserBrandModel.deleted_at.is_(None),
            )
            .order_by(UserBrandModel.created_at)
            .all()
        )

    def update_role(
        self, user_id: int, brand_id: int, new_role: BrandMembershipRole
    ) -> UserBrandModel | None:
        membership = self.get_membership(user_id, brand_id)
        if not membership:
            return None
        membership.role = new_role
        membership.updated_at = datetime.utcnow()
        return self.update(membership)

    def remove_membership(self, user_id: int, brand_id: int) -> bool:
        """Soft-delete a user's membership in a brand."""
        membership = self.get_membership(user_id, brand_id)
        if not membership:
            return False
        self.soft_delete(membership.id)
        return True
