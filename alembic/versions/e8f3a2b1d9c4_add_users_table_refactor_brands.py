"""add_users_table_refactor_brands

Revision ID: e8f3a2b1d9c4
Revises: c9d3e7f2a481
Create Date: 2026-03-23 00:00:00.000000

Changes:
- Create ``users`` table with role, brand_id FK, auth fields
- Drop user-specific columns from ``brands`` table:
  email, hashed_password, session_key, is_email_verified,
  email_verification_code, email_verification_expires_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f3a2b1d9c4'
down_revision: Union[str, None] = 'c9d3e7f2a481'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()

    # ── Create users table ────────────────────────────────────────────────────
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('hashed_password', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=False, server_default='NORMAL'),
            sa.Column('brand_id', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('email_verification_code', sa.String(), nullable=True),
            sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True),
            sa.Column('session_key', sa.String(), nullable=False, server_default='default_session'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['brand_id'], ['brands.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_users_id', 'users', ['id'])
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
        op.create_index('ix_users_brand_id', 'users', ['brand_id'])

    # ── Drop user-specific columns from brands ────────────────────────────────
    existing_brand_cols = {c['name'] for c in inspector.get_columns('brands')}

    cols_to_drop = [
        'email',
        'hashed_password',
        'session_key',
        'is_email_verified',
        'email_verification_code',
        'email_verification_expires_at',
    ]

    # Drop unique index on brands.email before dropping the column
    if 'email' in existing_brand_cols:
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('brands')}
        if 'ix_brands_email' in existing_indexes:
            op.drop_index('ix_brands_email', table_name='brands')

    for col in cols_to_drop:
        if col in existing_brand_cols:
            op.drop_column('brands', col)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_brand_cols = {c['name'] for c in inspector.get_columns('brands')}

    # ── Restore user-specific columns on brands ───────────────────────────────
    if 'email' not in existing_brand_cols:
        op.add_column('brands', sa.Column('email', sa.String(), nullable=True))
        op.create_index('ix_brands_email', 'brands', ['email'], unique=True)
    if 'hashed_password' not in existing_brand_cols:
        op.add_column('brands', sa.Column('hashed_password', sa.String(), nullable=True))
    if 'session_key' not in existing_brand_cols:
        op.add_column('brands', sa.Column('session_key', sa.String(), nullable=True))
    if 'is_email_verified' not in existing_brand_cols:
        op.add_column('brands', sa.Column('is_email_verified', sa.Boolean(), nullable=True, server_default='false'))
    if 'email_verification_code' not in existing_brand_cols:
        op.add_column('brands', sa.Column('email_verification_code', sa.String(), nullable=True))
    if 'email_verification_expires_at' not in existing_brand_cols:
        op.add_column('brands', sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True))

    # ── Drop users table ──────────────────────────────────────────────────────
    existing_tables = inspector.get_table_names()
    if 'users' in existing_tables:
        op.drop_index('ix_users_brand_id', table_name='users')
        op.drop_index('ix_users_email', table_name='users')
        op.drop_index('ix_users_id', table_name='users')
        op.drop_table('users')
