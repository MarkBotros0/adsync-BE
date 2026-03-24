import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    SUPER = "SUPER"
    ADMIN = "ADMIN"   # kept in enum for DB backwards-compat; no longer assigned to new users
    NORMAL = "NORMAL"


def _new_session_key() -> str:
    return str(uuid.uuid4())


class UserModel(Base):
    """User account.

    A user can belong to multiple brands via the UserBrandModel junction table.
    The global role on this model is used only for SUPER (platform-wide override).
    Brand-specific roles (ADMIN / NORMAL) live in UserBrandModel.role.
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

    # brand_memberships populated by UserBrandModel.user back-populates
    brand_memberships = relationship("UserBrandModel", back_populates="user", lazy="select")

    # Transient: set by _validate_user_and_brand so downstream code can read .brand
    brand = None

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
            "brand": self.brand.to_dict() if self.brand else None,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
