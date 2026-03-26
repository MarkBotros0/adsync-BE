from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class OrganizationMembershipModel(Base):
    """Links a user to an organization as an ORG_ADMIN.

    Org admins have access to all brands within the organization and can
    manage users and create brands (up to the subscription limit).
    Normal users are NOT represented here — they get per-brand access via UserBrandModel.
    """

    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_user_org"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    user = relationship("UserModel", back_populates="org_memberships")
    organization = relationship("OrganizationModel", back_populates="memberships")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<OrgMembership user_id={self.user_id} org_id={self.organization_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "created_at": self.created_at.isoformat(),
        }
