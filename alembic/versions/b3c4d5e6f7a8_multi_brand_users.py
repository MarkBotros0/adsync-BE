"""multi_brand_users

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 00:00:00.000000

Changes:
- Create ``brandmembershiprole`` PostgreSQL ENUM (ADMIN, NORMAL)
- Create ``user_brands`` junction table
- Backfill memberships from existing ``users.brand_id`` / ``users.role``
- Downgrade ADMIN users to NORMAL at the global level (role is now brand-scoped)
- Drop ``users.brand_id`` column
"""
import sqlalchemy as sa
from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_types = [t[0] for t in op.get_bind().execute(
        sa.text("SELECT typname FROM pg_type WHERE typtype = 'e'")
    ).fetchall()]

    # 1. Create brandmembershiprole enum (idempotent)
    if "brandmembershiprole" not in existing_types:
        op.execute("CREATE TYPE brandmembershiprole AS ENUM ('ADMIN', 'NORMAL')")

    # 2. Create user_brands table (idempotent)
    existing_tables = inspector.get_table_names()
    if "user_brands" not in existing_tables:
        op.create_table(
            "user_brands",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False),
            sa.Column(
                "role",
                sa.Enum("ADMIN", "NORMAL", name="brandmembershiprole", create_type=False),
                nullable=False,
                server_default="NORMAL",
            ),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("user_id", "brand_id", name="uq_user_brand"),
        )
        op.create_index("ix_user_brands_user_id", "user_brands", ["user_id"])
        op.create_index("ix_user_brands_brand_id", "user_brands", ["brand_id"])

    # 3. Backfill memberships from existing users
    #    SUPER and ADMIN users → ADMIN role in junction table
    #    NORMAL users          → NORMAL role in junction table
    op.execute(
        """
        INSERT INTO user_brands (user_id, brand_id, role, created_at, updated_at)
        SELECT
            id,
            brand_id,
            CASE WHEN role IN ('SUPER', 'ADMIN') THEN 'ADMIN'::brandmembershiprole
                 ELSE 'NORMAL'::brandmembershiprole
            END,
            NOW(),
            NOW()
        FROM users
        WHERE brand_id IS NOT NULL
          AND deleted_at IS NULL
        ON CONFLICT ON CONSTRAINT uq_user_brand DO NOTHING
        """
    )

    # 4. Downgrade ADMIN global role to NORMAL (brand-specific ADMIN is now in user_brands)
    op.execute("UPDATE users SET role = 'NORMAL'::userrole WHERE role = 'ADMIN'::userrole")

    # 5. Drop brand_id from users
    existing_columns = {c["name"] for c in inspector.get_columns("users")}
    if "brand_id" in existing_columns:
        # Make nullable first so existing NULL-ish data doesn't block the drop
        op.alter_column("users", "brand_id", nullable=True)
        # Drop FK constraint (name may differ — use inspector)
        fk_names = [fk["name"] for fk in inspector.get_foreign_keys("users")]
        for fk_name in fk_names:
            if fk_name and "brand" in fk_name.lower():
                op.drop_constraint(fk_name, "users", type_="foreignkey")
                break
        # Drop index if present
        indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_brand_id" in indexes:
            op.drop_index("ix_users_brand_id", table_name="users")
        op.drop_column("users", "brand_id")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {c["name"] for c in inspector.get_columns("users")}

    # 1. Restore brand_id column
    if "brand_id" not in existing_columns:
        op.add_column("users", sa.Column("brand_id", sa.Integer(), nullable=True))

    # 2. Restore first brand membership as brand_id
    op.execute(
        """
        UPDATE users u
        SET brand_id = (
            SELECT brand_id
            FROM user_brands ub
            WHERE ub.user_id = u.id AND ub.deleted_at IS NULL
            ORDER BY ub.created_at
            LIMIT 1
        )
        """
    )

    # 3. Restore ADMIN role for users who had ADMIN in any brand
    op.execute(
        """
        UPDATE users u
        SET role = 'ADMIN'::userrole
        WHERE EXISTS (
            SELECT 1 FROM user_brands ub
            WHERE ub.user_id = u.id
              AND ub.role = 'ADMIN'::brandmembershiprole
              AND ub.deleted_at IS NULL
        )
        AND u.role != 'SUPER'::userrole
        """
    )

    # 4. Drop user_brands table
    existing_tables = inspector.get_table_names()
    if "user_brands" in existing_tables:
        op.drop_index("ix_user_brands_brand_id", table_name="user_brands")
        op.drop_index("ix_user_brands_user_id", table_name="user_brands")
        op.drop_table("user_brands")

    # 5. Drop enum
    existing_types = [t[0] for t in op.get_bind().execute(
        sa.text("SELECT typname FROM pg_type WHERE typtype = 'e'")
    ).fetchall()]
    if "brandmembershiprole" in existing_types:
        op.execute("DROP TYPE brandmembershiprole")
