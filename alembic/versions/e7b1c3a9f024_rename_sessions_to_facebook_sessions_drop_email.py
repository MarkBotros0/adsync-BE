"""rename sessions to facebook_sessions, drop email column

Revision ID: e7b1c3a9f024
Revises: a3f92d1e5b0c
Create Date: 2026-03-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b1c3a9f024'
down_revision: Union[str, None] = 'a3f92d1e5b0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Rename sessions -> facebook_sessions
    if "sessions" in tables and "facebook_sessions" not in tables:
        op.rename_table("sessions", "facebook_sessions")

    # Re-inspect after potential rename
    inspector = sa.inspect(conn)
    target = "facebook_sessions" if "facebook_sessions" in inspector.get_table_names() else None
    if target:
        existing = {col["name"] for col in inspector.get_columns(target)}
        if "email" in existing:
            op.drop_column(target, "email")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Restore email column
    if "facebook_sessions" in tables:
        existing = {col["name"] for col in inspector.get_columns("facebook_sessions")}
        if "email" not in existing:
            op.add_column("facebook_sessions", sa.Column("email", sa.String(), nullable=True))

    # Rename back
    if "facebook_sessions" in tables and "sessions" not in tables:
        op.rename_table("facebook_sessions", "sessions")
