import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    SUPER = "SUPER"
    ADMIN = "ADMIN"
    NORMAL = "NORMAL"


def _new_session_key() -> str:
    return str(uuid.uuid4())


class UserModel(Base):
    """User account.

    Each user belongs to exactly one brand.
    Multiple users can share the same brand portal.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(
        SAEnum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.NORMAL,
    )

    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    brand = relationship("BrandModel", lazy="select")

    is_active = Column(Boolean, default=True, nullable=False)

    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_code = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)

    session_key = Column(String, nullable=False, default=_new_session_key)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "brand_id": self.brand_id,
            "brand": self.brand.to_dict() if self.brand else None,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
