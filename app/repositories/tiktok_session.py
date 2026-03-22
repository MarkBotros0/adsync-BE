from datetime import datetime

from sqlalchemy.orm import Session

from app.models.tiktok_session import TikTokSessionModel
from app.repositories.base import BaseRepository


class TikTokSessionRepository(BaseRepository[TikTokSessionModel]):
    """Repository for TikTok OAuth session operations."""

    def __init__(self, db: Session):
        super().__init__(TikTokSessionModel, db)

    def get_by_session_id(self, session_id: str) -> TikTokSessionModel | None:
        return self.get_by_field(session_id=session_id)

    def get_by_open_id(self, open_id: str) -> TikTokSessionModel | None:
        return self.get_by_field(open_id=open_id)

    def get_by_brand_id(self, brand_id: int) -> TikTokSessionModel | None:
        return (
            self.db.query(TikTokSessionModel)
            .filter(
                TikTokSessionModel.brand_id == brand_id,
                TikTokSessionModel.refresh_expires_at > datetime.utcnow(),
            )
            .order_by(TikTokSessionModel.created_at.desc())
            .first()
        )

    def create_session(
        self,
        session_id: str,
        open_id: str,
        display_name: str,
        access_token: str,
        expires_at: datetime,
        refresh_token: str,
        refresh_expires_at: datetime,
        brand_id: int | None = None,
    ) -> TikTokSessionModel:
        session = TikTokSessionModel(
            session_id=session_id,
            brand_id=brand_id,
            open_id=open_id,
            display_name=display_name,
            access_token=access_token,
            expires_at=expires_at,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )
        return self.create(session)

    def delete_session(self, session_id: str) -> bool:
        session = self.get_by_session_id(session_id)
        if session:
            self.delete(session)
            return True
        return False

    def is_valid(self, session_id: str) -> bool:
        """Returns True if the session exists and the refresh token has not expired."""
        session = self.get_by_session_id(session_id)
        if not session:
            return False
        return session.refresh_expires_at > datetime.utcnow()
