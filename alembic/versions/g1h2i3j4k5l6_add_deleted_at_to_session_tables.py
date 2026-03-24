"""add deleted_at to session tables

Revision ID: g1h2i3j4k5l6
Revises: e7b1c3a9f024
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in ("facebook_sessions", "instagram_sessions", "tiktok_sessions"):
        if table not in inspector.get_table_names():
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        if "deleted_at" not in existing:
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in ("facebook_sessions", "instagram_sessions", "tiktok_sessions"):
        op.drop_column(table, "deleted_at")
