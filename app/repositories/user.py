import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import UserModel, UserRole
from app.models.user_brand import UserBrandModel
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository for user account operations."""

    def __init__(self, db: Session):
        super().__init__(UserModel, db)

    def get_by_email(self, email: str) -> UserModel | None:
        return (
            self.db.query(UserModel)
            .filter(UserModel.email == email, UserModel.deleted_at.is_(None))
            .first()
        )

    def get_by_id(self, user_id: int) -> UserModel | None:
        return self.get(user_id)

    def get_by_brand(self, brand_id: int) -> list[UserModel]:
        """Return all active users that have a membership in the given brand."""
        return (
            self.db.query(UserModel)
            .join(UserBrandModel, UserBrandModel.user_id == UserModel.id)
            .filter(
                UserBrandModel.brand_id == brand_id,
                UserBrandModel.deleted_at.is_(None),
                UserModel.deleted_at.is_(None),
            )
            .order_by(UserModel.created_at)
            .all()
        )

    def get_all_users(self, skip: int = 0, limit: int = 200) -> list[UserModel]:
        return (
            self.db.query(UserModel)
            .filter(UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_user(
        self,
        email: str,
        hashed_password: str,
        name: str,
        role: UserRole = UserRole.NORMAL,
    ) -> UserModel:
        """Create a user record. Use UserBrandRepository.create_membership to link to brands."""
        user = UserModel(
            email=email,
            hashed_password=hashed_password,
            name=name,
            role=role,
            session_key=str(uuid.uuid4()),
        )
        return self.create(user)

    def rotate_session_key(self, user: UserModel) -> UserModel:
        user.session_key = str(uuid.uuid4())
        user.updated_at = datetime.utcnow()
        return self.update(user)

    def set_verification_code(self, user: UserModel, code: str, expires_at: datetime) -> UserModel:
        user.email_verification_code = code
        user.email_verification_expires_at = expires_at
        user.updated_at = datetime.utcnow()
        return self.update(user)

    def mark_email_verified(self, user: UserModel) -> UserModel:
        user.is_email_verified = True
        user.email_verification_code = None
        user.email_verification_expires_at = None
        user.updated_at = datetime.utcnow()
        return self.update(user)
