from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class TikTokSessionModel(Base):
    """
    TikTok OAuth session obtained via Login Kit.
    Stores a short-lived access token (24h) and a long-lived refresh token (365d).
    The access token must be refreshed using the refresh token before it expires.
    """

    __tablename__ = "tiktok_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    brand_id = Column(Integer, index=True, nullable=True)

    # TikTok user identifiers
    open_id = Column(String, index=True, nullable=False)
    display_name = Column(String)

    # Access token (24 hours) and refresh token (365 days)
    access_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    refresh_token = Column(String, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<TikTokSession {self.session_id}>"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "open_id": self.open_id,
            "display_name": self.display_name,
            "expires_at": self.expires_at.isoformat(),
            "refresh_expires_at": self.refresh_expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
