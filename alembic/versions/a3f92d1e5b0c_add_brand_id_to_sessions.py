"""add brand_id to sessions

Revision ID: a3f92d1e5b0c
Revises: c1681e410a59
Create Date: 2026-03-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f92d1e5b0c'
down_revision: Union[str, None] = 'c1681e410a59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Guard: only add if sessions table exists and column is missing
    tables = inspector.get_table_names()
    if "sessions" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("sessions")}
    if "brand_id" not in existing:
        op.add_column("sessions", sa.Column("brand_id", sa.Integer(), nullable=True))
        op.create_index("ix_sessions_brand_id", "sessions", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_brand_id", table_name="sessions")
    op.drop_column("sessions", "brand_id")
