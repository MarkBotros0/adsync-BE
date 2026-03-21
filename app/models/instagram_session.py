from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class InstagramSessionModel(Base):
    """
    Instagram OAuth session obtained via Business Login for Instagram.
    Stores an Instagram User access token — distinct from Facebook sessions.
    Token is long-lived (60 days) and can be refreshed before expiry.
    """

    __tablename__ = "instagram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    brand_id = Column(Integer, index=True, nullable=True)

    # Instagram user identifiers
    ig_user_id = Column(String, index=True, nullable=False)
    username = Column(String)

    # Long-lived Instagram User access token
    access_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<InstagramSession {self.session_id}>"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "ig_user_id": self.ig_user_id,
            "username": self.username,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
