"""Add competitor_targets, apify_runs; relax competitor_analysis_jobs.actors_total.

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k7l8m9n0o1p2'
down_revision: Union[str, None] = 'j6k7l8m9n0o1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'competitor_targets' not in existing_tables:
        op.create_table(
            'competitor_targets',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('competitor_id', sa.Integer(), sa.ForeignKey('competitors.id'), nullable=False),
            sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
            sa.Column('actor_key', sa.String(), nullable=False),
            sa.Column('target_value', sa.Text(), nullable=False),
            sa.Column('target_type', sa.String(), nullable=False, server_default='query'),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('last_run_at', sa.DateTime(), nullable=True),
            sa.Column('last_cost_usd', sa.Numeric(10, 4), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('competitor_id', 'actor_key', name='uq_targets_competitor_actor'),
        )
        op.create_index('ix_competitor_targets_id', 'competitor_targets', ['id'])
        op.create_index('ix_competitor_targets_competitor_id', 'competitor_targets', ['competitor_id'])
        op.create_index('ix_competitor_targets_brand_id', 'competitor_targets', ['brand_id'])
        op.create_index('ix_competitor_targets_actor_key', 'competitor_targets', ['actor_key'])

    if 'apify_runs' not in existing_tables:
        op.create_table(
            'apify_runs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
            sa.Column('competitor_id', sa.Integer(), sa.ForeignKey('competitors.id'), nullable=True),
            sa.Column('result_id', sa.Integer(), sa.ForeignKey('competitor_analysis_results.id'), nullable=True),
            sa.Column('actor_key', sa.String(), nullable=False),
            sa.Column('apify_run_id', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='running'),
            sa.Column('compute_units', sa.Numeric(12, 4), nullable=True),
            sa.Column('usage_total_usd', sa.Numeric(10, 4), nullable=True),
            sa.Column('dataset_id', sa.String(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_apify_runs_id', 'apify_runs', ['id'])
        op.create_index('ix_apify_runs_brand_id', 'apify_runs', ['brand_id'])
        op.create_index('ix_apify_runs_competitor_id', 'apify_runs', ['competitor_id'])
        op.create_index('ix_apify_runs_result_id', 'apify_runs', ['result_id'])
        op.create_index('ix_apify_runs_actor_key', 'apify_runs', ['actor_key'])
        op.create_index('ix_apify_runs_apify_run_id', 'apify_runs', ['apify_run_id'])
        op.create_index('ix_apify_runs_brand_created', 'apify_runs', ['brand_id', 'created_at'])

    # Relax competitor_analysis_jobs.actors_total: each scraper now runs as its
    # own job (actors_total=1 by default). Make nullable + default 1 so existing
    # rows remain valid and new single-actor jobs don't need to set it.
    if 'competitor_analysis_jobs' in existing_tables:
        cols = {c['name']: c for c in inspector.get_columns('competitor_analysis_jobs')}
        if 'actors_total' in cols and not cols['actors_total'].get('nullable', True):
            op.alter_column(
                'competitor_analysis_jobs',
                'actors_total',
                existing_type=sa.Integer(),
                nullable=True,
                server_default='1',
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'apify_runs' in existing_tables:
        op.drop_table('apify_runs')
    if 'competitor_targets' in existing_tables:
        op.drop_table('competitor_targets')

    if 'competitor_analysis_jobs' in existing_tables:
        op.alter_column(
            'competitor_analysis_jobs',
            'actors_total',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='0',
        )
