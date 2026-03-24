import enum
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class BrandMembershipRole(str, enum.Enum):
    ADMIN = "ADMIN"
    NORMAL = "NORMAL"


class UserBrandModel(Base):
    """Junction table linking users to brands with a brand-specific role.

    A user can belong to multiple brands, with a different role in each.
    The role here (ADMIN / NORMAL) is brand-scoped; the global SUPER role
    lives on UserModel.role and bypasses all brand-level checks.
    """

    __tablename__ = "user_brands"
    __table_args__ = (UniqueConstraint("user_id", "brand_id", name="uq_user_brand"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    role = Column(
        SAEnum(BrandMembershipRole, name="brandmembershiprole"),
        nullable=False,
        default=BrandMembershipRole.NORMAL,
    )

    user = relationship("UserModel", back_populates="brand_memberships")
    brand = relationship("BrandModel", lazy="select")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<UserBrand user_id={self.user_id} brand_id={self.brand_id} role={self.role}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "brand_id": self.brand_id,
            "role": self.role.value if isinstance(self.role, BrandMembershipRole) else self.role,
            "brand": self.brand.to_dict() if self.brand else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
