import secrets
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.user import UserRole


def _new_token() -> str:
    """Generate a cryptographically secure URL-safe 32-byte invitation token."""
    return secrets.token_urlsafe(32)


class InvitationModel(Base):
    """One-time invitation link sent to a new user.

    Valid for 24 hours and single-use (``accepted_at`` is set on acceptance).
    """

    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    role = Column(SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.NORMAL)
    token = Column(String, unique=True, nullable=False, index=True, default=_new_token)
    expires_at = Column(DateTime, nullable=False)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True, default=None)

    brand = relationship("BrandModel", lazy="select")
    invited_by = relationship("UserModel", foreign_keys=[invited_by_user_id], lazy="select")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def is_valid(self) -> bool:
        return self.accepted_at is None and datetime.utcnow() < self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "brand_id": self.brand_id,
            "brand_name": self.brand.name if self.brand else None,
            "role": self.role,
            "expires_at": self.expires_at.isoformat(),
            "accepted": self.accepted_at is not None,
            "created_at": self.created_at.isoformat(),
        }
