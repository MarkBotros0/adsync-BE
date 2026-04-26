"""Add competitor analysis tables.

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'j6k7l8m9n0o1'
down_revision: Union[str, None] = 'i5j6k7l8m9n0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if 'competitors' not in existing_tables:
        op.create_table(
            'competitors',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('slug', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('brand_id', 'slug', name='uq_competitors_brand_slug'),
        )
        op.create_index('ix_competitors_id', 'competitors', ['id'])
        op.create_index('ix_competitors_brand_id', 'competitors', ['brand_id'])
        op.create_index('ix_competitors_slug', 'competitors', ['slug'])

    if 'competitor_analysis_jobs' not in existing_tables:
        op.create_table(
            'competitor_analysis_jobs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('competitor_id', sa.Integer(), sa.ForeignKey('competitors.id'), nullable=False),
            sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('actors_total', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('actors_done', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('actors_failed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_competitor_analysis_jobs_id', 'competitor_analysis_jobs', ['id'])
        op.create_index('ix_competitor_analysis_jobs_competitor_id', 'competitor_analysis_jobs', ['competitor_id'])
        op.create_index('ix_competitor_analysis_jobs_brand_id', 'competitor_analysis_jobs', ['brand_id'])
        op.create_index('ix_competitor_analysis_jobs_status', 'competitor_analysis_jobs', ['status'])

    if 'competitor_analysis_results' not in existing_tables:
        op.create_table(
            'competitor_analysis_results',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('job_id', sa.Integer(), sa.ForeignKey('competitor_analysis_jobs.id'), nullable=False),
            sa.Column('competitor_id', sa.Integer(), sa.ForeignKey('competitors.id'), nullable=False),
            sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=False),
            sa.Column('actor_key', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('apify_run_id', sa.String(), nullable=True),
            sa.Column('data', JSONB(), nullable=True),
            sa.Column('summary', JSONB(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('job_id', 'actor_key', name='uq_results_job_actor'),
        )
        op.create_index('ix_competitor_analysis_results_id', 'competitor_analysis_results', ['id'])
        op.create_index('ix_competitor_analysis_results_job_id', 'competitor_analysis_results', ['job_id'])
        op.create_index('ix_competitor_analysis_results_competitor_id', 'competitor_analysis_results', ['competitor_id'])
        op.create_index('ix_competitor_analysis_results_brand_id', 'competitor_analysis_results', ['brand_id'])
        op.create_index('ix_competitor_analysis_results_actor_key', 'competitor_analysis_results', ['actor_key'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if 'competitor_analysis_results' in existing_tables:
        op.drop_table('competitor_analysis_results')
    if 'competitor_analysis_jobs' in existing_tables:
        op.drop_table('competitor_analysis_jobs')
    if 'competitors' in existing_tables:
        op.drop_table('competitors')
