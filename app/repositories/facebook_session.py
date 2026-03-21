from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.facebook_session import FacebookSessionModel
from app.repositories.base import BaseRepository


class FacebookSessionRepository(BaseRepository[FacebookSessionModel]):
    """Repository for Facebook OAuth session operations"""

    def __init__(self, db: Session):
        super().__init__(FacebookSessionModel, db)

    def get_by_session_id(self, session_id: str) -> Optional[FacebookSessionModel]:
        """Get session by session_id"""
        return self.get_by_field(session_id=session_id)

    def get_by_user_id(self, user_id: str) -> Optional[FacebookSessionModel]:
        """Get session by Facebook user_id"""
        return self.get_by_field(user_id=user_id)

    def get_by_brand_id(self, brand_id: int) -> Optional[FacebookSessionModel]:
        """Get the most recent valid session for a brand"""
        from datetime import datetime as _dt
        return (
            self.db.query(FacebookSessionModel)
            .filter(FacebookSessionModel.brand_id == brand_id, FacebookSessionModel.expires_at > _dt.utcnow())
            .order_by(FacebookSessionModel.created_at.desc())
            .first()
        )

    def create_session(self, session_id: str, user_id: str, user_name: str,
                       access_token: str, expires_at: datetime,
                       brand_id: Optional[int] = None) -> FacebookSessionModel:
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
                     expires_at: datetime) -> Optional[FacebookSessionModel]:
        """Update session token"""
        session = self.get_by_session_id(session_id)
        if session:
            session.access_token = access_token
            session.expires_at = expires_at
            session.updated_at = datetime.utcnow()
            return self.update(session)
        return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session by session_id"""
        session = self.get_by_session_id(session_id)
        if session:
            self.delete(session)
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
