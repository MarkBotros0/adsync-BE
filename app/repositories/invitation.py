from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.invitation import InvitationModel
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[InvitationModel]):
    """Repository for invitation operations."""

    def __init__(self, db: Session):
        super().__init__(InvitationModel, db)

    def create_invitation(
        self,
        email: str,
        brand_id: int,
        role: str,
        invited_by_user_id: int | None,
        expires_hours: int = 24,
    ) -> InvitationModel:
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        invitation = InvitationModel(
            email=email,
            brand_id=brand_id,
            role=role,
            expires_at=expires_at,
            invited_by_user_id=invited_by_user_id,
        )
        return self.create(invitation)

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
