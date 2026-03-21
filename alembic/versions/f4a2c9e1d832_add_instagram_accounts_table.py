"""add_instagram_accounts_table

Revision ID: f4a2c9e1d832
Revises: d36ad8bea3c8
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a2c9e1d832'
down_revision: Union[str, None] = 'd36ad8bea3c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'instagram_accounts' in inspector.get_table_names():
        return  # idempotent — already exists

    op.create_table(
        'instagram_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('facebook_session_id', sa.String(), nullable=False),
        sa.Column('ig_user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('biography', sa.String(), nullable=True),
        sa.Column('profile_picture_url', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('follows_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('media_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('page_id', sa.String(), nullable=False),
        sa.Column('page_name', sa.String(), nullable=True),
        sa.Column('page_access_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('facebook_session_id', 'ig_user_id', name='uq_session_ig_user'),
    )
    op.create_index('ix_instagram_accounts_id', 'instagram_accounts', ['id'])
    op.create_index('ix_instagram_accounts_facebook_session_id', 'instagram_accounts', ['facebook_session_id'])
    op.create_index('ix_instagram_accounts_ig_user_id', 'instagram_accounts', ['ig_user_id'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'instagram_accounts' not in inspector.get_table_names():
        return
    op.drop_index('ix_instagram_accounts_ig_user_id', table_name='instagram_accounts')
    op.drop_index('ix_instagram_accounts_facebook_session_id', table_name='instagram_accounts')
    op.drop_index('ix_instagram_accounts_id', table_name='instagram_accounts')
    op.drop_table('instagram_accounts')
