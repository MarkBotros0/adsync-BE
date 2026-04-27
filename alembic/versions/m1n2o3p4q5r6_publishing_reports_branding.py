"""Publishing, reports, branding, campaign tags — Part B + marketing-expert tables.

Revision ID: m1n2o3p4q5r6
Revises: k7l8m9n0o1p2
Create Date: 2026-04-27

Idempotent ``CREATE TABLE IF NOT EXISTS`` semantics — every block first checks the
inspector so the migration is safe to re-run after a partial failure (per CLAUDE.md
migration conventions).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, None] = "k7l8m9n0o1p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # ── Campaign tags ─────────────────────────────────────────────────────
    if "campaign_tags" not in existing:
        op.create_table(
            "campaign_tags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False, index=True),
            sa.Column("color", sa.String(), nullable=False, server_default="#6366f1"),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("brand_id", "slug", name="uq_campaign_tags_brand_slug"),
        )

    if "post_campaign_tags" not in existing:
        op.create_table(
            "post_campaign_tags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("campaign_tags.id"), nullable=False, index=True),
            sa.Column("platform", sa.String(), nullable=False, index=True),
            sa.Column("post_id", sa.String(), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "brand_id", "platform", "post_id", "tag_id",
                name="uq_post_campaign_tags_brand_platform_post_tag",
            ),
        )

    # ── Media library (BYTEA inline storage) ──────────────────────────────
    if "media_assets" not in existing:
        op.create_table(
            "media_assets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("uploader_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("mime", sa.String(), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )

    # ── Scheduled posts (composer + calendar + approval workflow) ─────────
    if "scheduled_posts" not in existing:
        op.create_table(
            "scheduled_posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="draft", index=True),
            sa.Column("scheduled_at", sa.DateTime(), nullable=True, index=True),
            sa.Column("text", sa.Text(), nullable=False, server_default=""),
            sa.Column("platforms_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("per_platform_payload_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("media_asset_ids_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("campaign_tag_ids_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("approval_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("platform_post_ids_json", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )

    # ── Reports ───────────────────────────────────────────────────────────
    if "report_schedules" not in existing:
        op.create_table(
            "report_schedules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("cadence", sa.String(), nullable=False, server_default="weekly"),
            sa.Column("recipients_csv", sa.Text(), nullable=False),
            sa.Column("template_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("last_sent_at", sa.DateTime(), nullable=True),
            sa.Column("next_sent_at", sa.DateTime(), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )

    if "report_runs" not in existing:
        op.create_table(
            "report_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("report_schedules.id"), nullable=True, index=True),
            sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("period_start", sa.DateTime(), nullable=False),
            sa.Column("period_end", sa.DateTime(), nullable=False),
            sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("csv_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("generated_at", sa.DateTime(), nullable=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )

    # ── Brand identity (white-label) ──────────────────────────────────────
    if "brand_identities" not in existing:
        op.create_table(
            "brand_identities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("logo_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("logo_mime", sa.String(), nullable=True),
            sa.Column("logo_filename", sa.String(), nullable=True),
            sa.Column("primary_color", sa.String(), nullable=False, server_default="#6366f1"),
            sa.Column("secondary_color", sa.String(), nullable=False, server_default="#0ea5e9"),
            sa.Column("font_family", sa.String(), nullable=False, server_default="Inter"),
            sa.Column("white_label_subdomain", sa.String(), nullable=True, unique=True, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("brand_id", name="uq_brand_identities_brand"),
        )

    # ── Client views (agency invites its end-clients) ─────────────────────
    if "client_views" not in existing:
        op.create_table(
            "client_views",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("allowed_pages_json", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("brand_id", "user_id", name="uq_client_views_brand_user"),
        )


def downgrade() -> None:
    # Drop in reverse-creation order so FKs unwind cleanly.
    for table in (
        "client_views",
        "brand_identities",
        "report_runs",
        "report_schedules",
        "scheduled_posts",
        "media_assets",
        "post_campaign_tags",
        "campaign_tags",
    ):
        op.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
