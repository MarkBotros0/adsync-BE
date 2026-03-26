from sqlalchemy.orm import Session
from app.models.organization_membership import OrganizationMembershipModel
from app.repositories.base import BaseRepository


class OrganizationMembershipRepository(BaseRepository[OrganizationMembershipModel]):
    """Repository for org admin membership operations."""

    def __init__(self, db: Session):
        super().__init__(OrganizationMembershipModel, db)

    def get_membership(self, user_id: int, org_id: int) -> OrganizationMembershipModel | None:
        return (
            self.db.query(OrganizationMembershipModel)
            .filter(
                OrganizationMembershipModel.user_id == user_id,
                OrganizationMembershipModel.organization_id == org_id,
                OrganizationMembershipModel.deleted_at.is_(None),
            )
            .first()
        )

    def get_orgs_for_user(self, user_id: int) -> list[OrganizationMembershipModel]:
        return (
            self.db.query(OrganizationMembershipModel)
            .filter(
                OrganizationMembershipModel.user_id == user_id,
                OrganizationMembershipModel.deleted_at.is_(None),
            )
            .all()
        )

    def get_admins_for_org(self, org_id: int) -> list[OrganizationMembershipModel]:
        return (
            self.db.query(OrganizationMembershipModel)
            .filter(
                OrganizationMembershipModel.organization_id == org_id,
                OrganizationMembershipModel.deleted_at.is_(None),
            )
            .all()
        )

    def create_membership(self, user_id: int, org_id: int) -> OrganizationMembershipModel:
        membership = OrganizationMembershipModel(
            user_id=user_id,
            organization_id=org_id,
        )
        return self.create(membership)

    def remove_membership(self, user_id: int, org_id: int) -> bool:
        membership = self.get_membership(user_id, org_id)
        if not membership:
            return False
        self.soft_delete(membership.id)
        return True
