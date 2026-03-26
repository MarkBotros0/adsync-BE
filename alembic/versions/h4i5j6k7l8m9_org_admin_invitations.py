"""Make invitations.brand_id nullable and add organization_id for org-level invites.

Revision ID: h4i5j6k7l8m9
Revises: ee874709b61e
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'h4i5j6k7l8m9'
down_revision = 'ee874709b61e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c['name'] for c in inspector.get_columns('invitations')}

    # Make brand_id nullable (was NOT NULL)
    if 'brand_id' in columns:
        op.alter_column('invitations', 'brand_id', nullable=True)

    # Add organization_id for org-level (ORG_ADMIN) invitations
    if 'organization_id' not in columns:
        op.add_column(
            'invitations',
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        )
        op.create_index('ix_invitations_organization_id', 'invitations', ['organization_id'])


def downgrade() -> None:
    op.drop_index('ix_invitations_organization_id', table_name='invitations')
    op.drop_column('invitations', 'organization_id')
    op.alter_column('invitations', 'brand_id', nullable=False)
