from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class OrganizationModel(Base):
    """Top-level tenant — represents a marketing agency.

    An organization owns a subscription and has many brands.
    Users are linked to an organization as ORG_ADMIN via OrganizationMembershipModel.
    """

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    subscription = relationship("SubscriptionModel", lazy="select")

    brands = relationship(
        "BrandModel",
        back_populates="organization",
        lazy="select",
        primaryjoin="and_(BrandModel.organization_id == OrganizationModel.id, BrandModel.deleted_at.is_(None))",
    )

    memberships = relationship(
        "OrganizationMembershipModel",
        back_populates="organization",
        lazy="select",
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "logo_url": self.logo_url,
            "is_active": self.is_active,
            "subscription": self.subscription.to_dict() if self.subscription else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
