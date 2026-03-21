"""add_instagram_sessions_table

Revision ID: b2e5f8a1c347
Revises: f4a2c9e1d832
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2e5f8a1c347'
down_revision: Union[str, None] = 'f4a2c9e1d832'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'instagram_sessions' in inspector.get_table_names():
        return  # idempotent — already exists

    op.create_table(
        'instagram_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('ig_user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index('ix_instagram_sessions_id', 'instagram_sessions', ['id'])
    op.create_index('ix_instagram_sessions_session_id', 'instagram_sessions', ['session_id'], unique=True)
    op.create_index('ix_instagram_sessions_brand_id', 'instagram_sessions', ['brand_id'])
    op.create_index('ix_instagram_sessions_ig_user_id', 'instagram_sessions', ['ig_user_id'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'instagram_sessions' not in inspector.get_table_names():
        return
    op.drop_index('ix_instagram_sessions_ig_user_id', table_name='instagram_sessions')
    op.drop_index('ix_instagram_sessions_brand_id', table_name='instagram_sessions')
    op.drop_index('ix_instagram_sessions_session_id', table_name='instagram_sessions')
    op.drop_index('ix_instagram_sessions_id', table_name='instagram_sessions')
    op.drop_table('instagram_sessions')
