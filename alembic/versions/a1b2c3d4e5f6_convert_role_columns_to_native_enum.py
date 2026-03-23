"""convert_role_columns_to_native_enum

Revision ID: a1b2c3d4e5f6
Revises: 6082ef70ae7f
Create Date: 2026-03-23 00:00:00.000000

Changes:
- Create PostgreSQL native ENUM type ``userrole`` (SUPER, ADMIN, NORMAL)
- Convert ``users.role`` from VARCHAR to ``userrole``
- Convert ``invitations.role`` from VARCHAR to ``userrole``
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6082ef70ae7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the native enum type (idempotent via exception handler)
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('SUPER', 'ADMIN', 'NORMAL');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    inspector = sa.inspect(op.get_bind())

    # Convert users.role VARCHAR → userrole
    users_role_type = next(
        (c['type'] for c in inspector.get_columns('users') if c['name'] == 'role'), None
    )
    if users_role_type is not None and not isinstance(users_role_type, sa.Enum):
        op.execute(sa.text(
            "ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole"
        ))

    # Convert invitations.role VARCHAR → userrole
    inv_role_type = next(
        (c['type'] for c in inspector.get_columns('invitations') if c['name'] == 'role'), None
    )
    if inv_role_type is not None and not isinstance(inv_role_type, sa.Enum):
        op.execute(sa.text(
            "ALTER TABLE invitations ALTER COLUMN role TYPE userrole USING role::userrole"
        ))


def downgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE invitations ALTER COLUMN role TYPE VARCHAR USING role::VARCHAR"
    ))
    op.execute(sa.text(
        "ALTER TABLE users ALTER COLUMN role TYPE VARCHAR USING role::VARCHAR"
    ))
    op.execute(sa.text("DROP TYPE IF EXISTS userrole"))
