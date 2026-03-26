"""Drop subscription_id from brands table.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'i5j6k7l8m9n0'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c['name'] for c in inspector.get_columns('brands')}
    if 'subscription_id' in columns:
        # Drop FK constraint first (SQLite-compatible: drop and recreate not needed, just drop column)
        with op.batch_alter_table('brands') as batch_op:
            batch_op.drop_column('subscription_id')


def downgrade() -> None:
    with op.batch_alter_table('brands') as batch_op:
        batch_op.add_column(sa.Column('subscription_id', sa.Integer(), nullable=True))
