
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.facebook_session import FacebookSessionModel
from app.repositories.base import BaseRepository


class FacebookSessionRepository(BaseRepository[FacebookSessionModel]):
    """Repository for Facebook OAuth session operations"""

    def __init__(self, db: Session):
        super().__init__(FacebookSessionModel, db)

    def get_by_session_id(self, session_id: str) -> FacebookSessionModel | None:
        """Get session by session_id"""
        return self.get_by_field(session_id=session_id)

    def get_by_user_id(self, user_id: str) -> FacebookSessionModel | None:
        """Get session by Facebook user_id"""
        return self.get_by_field(user_id=user_id)

    def get_by_brand_id(self, brand_id: int) -> FacebookSessionModel | None:
        """Get the most recent valid session for a brand"""
        return (
            self.db.query(FacebookSessionModel)
            .filter(
                FacebookSessionModel.brand_id == brand_id,
                FacebookSessionModel.expires_at > datetime.utcnow(),
                FacebookSessionModel.deleted_at.is_(None),
            )
            .order_by(FacebookSessionModel.created_at.desc())
            .first()
        )

    def create_session(self, session_id: str, user_id: str, user_name: str,
                       access_token: str, expires_at: datetime,
                       brand_id: int | None = None) -> FacebookSessionModel:
        """Create new Facebook session"""
        session = FacebookSessionModel(
            session_id=session_id,
            brand_id=brand_id,
            user_id=user_id,
            user_name=user_name,
            access_token=access_token,
            expires_at=expires_at,
        )
        return self.create(session)

    def update_token(self, session_id: str, access_token: str,
                     expires_at: datetime) -> FacebookSessionModel | None:
        """Update session token"""
        session = self.get_by_session_id(session_id)
        if session:
            session.access_token = access_token
            session.expires_at = expires_at
            session.updated_at = datetime.utcnow()
            return self.update(session)
        return None

    def delete_session(self, session_id: str) -> bool:
        """Soft-delete session by session_id"""
        session = self.get_by_session_id(session_id)
        if session:
            session.deleted_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Delete all expired sessions"""
        now = datetime.utcnow()
        expired = self.db.query(FacebookSessionModel).filter(
            FacebookSessionModel.expires_at < now
        ).all()
        count = len(expired)
        for session in expired:
            self.delete(session)
        return count

    def is_valid(self, session_id: str) -> bool:
        """Check if session exists and is not expired"""
        session = self.get_by_session_id(session_id)
        if not session:
            return False
        return session.expires_at > datetime.utcnow()
