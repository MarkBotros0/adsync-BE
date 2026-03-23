"""add_invitations_and_soft_delete

Revision ID: f1a2b3c4d5e6
Revises: e8f3a2b1d9c4
Create Date: 2026-03-23 01:00:00.000000

Changes:
- Add ``invitations`` table for invitation links
- Add ``deleted_at`` column to brands, users (soft-delete support)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e8f3a2b1d9c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()

    # ── Add deleted_at to brands ──────────────────────────────────────────────
    brand_cols = {c['name'] for c in inspector.get_columns('brands')}
    if 'deleted_at' not in brand_cols:
        op.add_column('brands', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # ── Add deleted_at to users ───────────────────────────────────────────────
    if 'users' in existing_tables:
        user_cols = {c['name'] for c in inspector.get_columns('users')}
        if 'deleted_at' not in user_cols:
            op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # ── Create invitations table ──────────────────────────────────────────────
    if 'invitations' not in existing_tables:
        op.create_table(
            'invitations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('brand_id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(), nullable=False, server_default='NORMAL'),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('invited_by_user_id', sa.Integer(), nullable=False),
            sa.Column('accepted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['brand_id'], ['brands.id']),
            sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_invitations_id', 'invitations', ['id'])
        op.create_index('ix_invitations_email', 'invitations', ['email'])
        op.create_index('ix_invitations_brand_id', 'invitations', ['brand_id'])
        op.create_index('ix_invitations_token', 'invitations', ['token'], unique=True)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()

    if 'invitations' in existing_tables:
        op.drop_index('ix_invitations_token', table_name='invitations')
        op.drop_index('ix_invitations_brand_id', table_name='invitations')
        op.drop_index('ix_invitations_email', table_name='invitations')
        op.drop_index('ix_invitations_id', table_name='invitations')
        op.drop_table('invitations')

    if 'users' in existing_tables:
        user_cols = {c['name'] for c in inspector.get_columns('users')}
        if 'deleted_at' in user_cols:
            op.drop_column('users', 'deleted_at')

    brand_cols = {c['name'] for c in inspector.get_columns('brands')}
    if 'deleted_at' in brand_cols:
        op.drop_column('brands', 'deleted_at')
