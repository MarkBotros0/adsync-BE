from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.invitation import InvitationModel
from app.repositories.base import BaseRepository


def _norm(email: str) -> str:
    return email.strip().lower() if isinstance(email, str) else email


class InvitationRepository(BaseRepository[InvitationModel]):
    """Repository for invitation operations."""

    def __init__(self, db: Session):
        super().__init__(InvitationModel, db)

    def create_invitation(
        self,
        email: str,
        role: str,
        invited_by_user_id: int | None,
        brand_id: int | None = None,
        organization_id: int | None = None,
        expires_hours: int = 24,
    ) -> InvitationModel:
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        invitation = InvitationModel(
            email=_norm(email),
            brand_id=brand_id,
            organization_id=organization_id,
            role=role,
            expires_at=expires_at,
            invited_by_user_id=invited_by_user_id,
        )
        return self.create(invitation)

    def get_pending_by_email_and_org(self, email: str, org_id: int) -> InvitationModel | None:
        """Return an active org-level (ORG_ADMIN) invite for this email+org pair."""
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.email == _norm(email),
                InvitationModel.organization_id == org_id,
                InvitationModel.brand_id.is_(None),
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
                InvitationModel.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_token(self, token: str) -> InvitationModel | None:
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.token == token,
                InvitationModel.deleted_at.is_(None),
            )
            .first()
        )

    def mark_accepted(self, invitation: InvitationModel) -> InvitationModel:
        invitation.accepted_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()
        return self.update(invitation)

    def get_all_pending(self) -> list[InvitationModel]:
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
                InvitationModel.deleted_at.is_(None),
            )
            .order_by(InvitationModel.created_at.desc())
            .all()
        )

    def get_all_invitations(self) -> list[InvitationModel]:
        """Return all non-deleted invitations across all brands (for SUPER view)."""
        return (
            self.db.query(InvitationModel)
            .filter(InvitationModel.deleted_at.is_(None))
            .order_by(InvitationModel.created_at.desc())
            .all()
        )

    def get_pending_by_email_and_brand(self, email: str, brand_id: int) -> InvitationModel | None:
        """Return an active (non-expired, non-accepted) invitation for this email+brand pair."""
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.email == _norm(email),
                InvitationModel.brand_id == brand_id,
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
                InvitationModel.deleted_at.is_(None),
            )
            .first()
        )

    def get_pending_by_brand(self, brand_id: int) -> list[InvitationModel]:
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.brand_id == brand_id,
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
                InvitationModel.deleted_at.is_(None),
            )
            .order_by(InvitationModel.created_at.desc())
            .all()
        )

    def get_pending_by_org(self, organization_id: int) -> list[InvitationModel]:
        """Return pending ORG_ADMIN invitations scoped to an organization (brand_id is NULL)."""
        return (
            self.db.query(InvitationModel)
            .filter(
                InvitationModel.organization_id == organization_id,
                InvitationModel.brand_id.is_(None),
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow(),
                InvitationModel.deleted_at.is_(None),
            )
            .order_by(InvitationModel.created_at.desc())
            .all()
        )
