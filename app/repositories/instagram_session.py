from datetime import datetime

from sqlalchemy.orm import Session

from app.models.instagram_session import InstagramSessionModel
from app.repositories.base import BaseRepository


class InstagramSessionRepository(BaseRepository[InstagramSessionModel]):
    """Repository for Instagram OAuth session operations."""

    def __init__(self, db: Session):
        super().__init__(InstagramSessionModel, db)

    def get_by_session_id(self, session_id: str) -> InstagramSessionModel | None:
        return self.get_by_field(session_id=session_id)

    def get_by_ig_user_id(self, ig_user_id: str) -> InstagramSessionModel | None:
        return self.get_by_field(ig_user_id=ig_user_id)

    def get_by_brand_id(self, brand_id: int) -> InstagramSessionModel | None:
        return (
            self.db.query(InstagramSessionModel)
            .filter(
                InstagramSessionModel.brand_id == brand_id,
                InstagramSessionModel.expires_at > datetime.utcnow(),
            )
            .order_by(InstagramSessionModel.created_at.desc())
            .first()
        )

    def create_session(
        self,
        session_id: str,
        ig_user_id: str,
        username: str,
        access_token: str,
        expires_at: datetime,
        brand_id: int | None = None,
    ) -> InstagramSessionModel:
        session = InstagramSessionModel(
            session_id=session_id,
            brand_id=brand_id,
            ig_user_id=ig_user_id,
            username=username,
            access_token=access_token,
            expires_at=expires_at,
        )
        return self.create(session)

    def delete_session(self, session_id: str) -> bool:
        session = self.get_by_session_id(session_id)
        if session:
            self.delete(session)
            return True
        return False

    def is_valid(self, session_id: str) -> bool:
        session = self.get_by_session_id(session_id)
        if not session:
            return False
        return session.expires_at > datetime.utcnow()
