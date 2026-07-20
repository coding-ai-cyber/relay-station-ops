"""sub2api instances

Revision ID: 20260713_0002
Revises: 20260713_0001
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0002"
down_revision: str | None = "20260713_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sub2api_instances",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("admin_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_probe_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_probe_status", sa.String(length=50), nullable=True),
        sa.Column("last_probe_message", sa.Text(), nullable=True),
        sa.Column("detected_accounts_path", sa.String(length=200), nullable=True),
        sa.Column("detected_version", sa.String(length=100), nullable=True),
        sa.Column("adapter", sa.String(length=50), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sub2api_instances_is_active"), "sub2api_instances", ["is_active"], unique=False)
    op.create_index(op.f("ix_sub2api_instances_last_probe_status"), "sub2api_instances", ["last_probe_status"], unique=False)
    op.create_index(op.f("ix_sub2api_instances_name"), "sub2api_instances", ["name"], unique=False)

    op.add_column("account_check_batches", sa.Column("sub2api_instance_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_account_check_batches_sub2api_instance_id"),
        "account_check_batches",
        ["sub2api_instance_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_account_check_batches_sub2api_instance_id",
        "account_check_batches",
        "sub2api_instances",
        ["sub2api_instance_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_account_check_batches_sub2api_instance_id",
        "account_check_batches",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_account_check_batches_sub2api_instance_id"),
        table_name="account_check_batches",
    )
    op.drop_column("account_check_batches", "sub2api_instance_id")
    op.drop_index(op.f("ix_sub2api_instances_name"), table_name="sub2api_instances")
    op.drop_index(op.f("ix_sub2api_instances_last_probe_status"), table_name="sub2api_instances")
    op.drop_index(op.f("ix_sub2api_instances_is_active"), table_name="sub2api_instances")
    op.drop_table("sub2api_instances")
