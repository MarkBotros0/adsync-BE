"""drop_sessions_table

Revision ID: d36ad8bea3c8
Revises: e7b1c3a9f024
Create Date: 2026-03-21 17:45:40.258909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd36ad8bea3c8'
down_revision: Union[str, None] = 'e7b1c3a9f024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
