import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def _new_session_key() -> str:
    """Generate a fresh session key (used for force sign-out)."""
    return str(uuid.uuid4())


class BrandModel(Base):
    """Brand account database model.

    Each brand is an independent account that can authenticate via JWT.
    The ``session_key`` acts as a server-side nonce embedded in every JWT;
    rotating it immediately invalidates all previously issued tokens,
    enabling force sign-out.
    """

    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Subscription relation
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    subscription = relationship("SubscriptionModel", lazy="select")

    # Email verification
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_code = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)

    # Session key: rotating this key forces all existing JWTs to be invalid
    session_key = Column(String, nullable=False, default=_new_session_key)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Brand {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "logo_url": self.logo_url,
            "website": self.website,
            "industry": self.industry,
            "is_active": self.is_active,
            "subscription": self.subscription.to_dict() if self.subscription else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
