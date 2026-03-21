from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class FacebookSessionModel(Base):
    """Facebook OAuth session database model"""

    __tablename__ = "facebook_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    brand_id = Column(Integer, index=True, nullable=True)
    user_id = Column(String, index=True, nullable=False)
    user_name = Column(String)
    access_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FacebookSession {self.session_id}>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
