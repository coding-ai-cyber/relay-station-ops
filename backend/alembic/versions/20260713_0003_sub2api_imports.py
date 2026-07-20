"""sub2api import batches

Revision ID: 20260713_0003
Revises: 20260713_0002
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0003"
down_revision: str | None = "20260713_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sub2api_import_batches",
        sa.Column("batch_no", sa.String(length=100), nullable=False),
        sa.Column("instance_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("retry_of_batch_id", sa.UUID(), nullable=True),
        sa.Column("group_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("duplicate_policy", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["sub2api_instances.id"]),
        sa.ForeignKeyConstraint(["retry_of_batch_id"], ["sub2api_import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sub2api_import_batches_batch_no"), "sub2api_import_batches", ["batch_no"], unique=True)
    op.create_index(op.f("ix_sub2api_import_batches_created_by"), "sub2api_import_batches", ["created_by"], unique=False)
    op.create_index(op.f("ix_sub2api_import_batches_instance_id"), "sub2api_import_batches", ["instance_id"], unique=False)
    op.create_index(op.f("ix_sub2api_import_batches_retry_of_batch_id"), "sub2api_import_batches", ["retry_of_batch_id"], unique=False)
    op.create_index(op.f("ix_sub2api_import_batches_status"), "sub2api_import_batches", ["status"], unique=False)

    op.create_table(
        "sub2api_import_items",
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("remote_account_id", sa.String(length=200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["sub2api_import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sub2api_import_items_account_id"), "sub2api_import_items", ["account_id"], unique=False)
    op.create_index(op.f("ix_sub2api_import_items_batch_id"), "sub2api_import_items", ["batch_id"], unique=False)
    op.create_index(op.f("ix_sub2api_import_items_remote_account_id"), "sub2api_import_items", ["remote_account_id"], unique=False)
    op.create_index(op.f("ix_sub2api_import_items_status"), "sub2api_import_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sub2api_import_items_status"), table_name="sub2api_import_items")
    op.drop_index(op.f("ix_sub2api_import_items_remote_account_id"), table_name="sub2api_import_items")
    op.drop_index(op.f("ix_sub2api_import_items_batch_id"), table_name="sub2api_import_items")
    op.drop_index(op.f("ix_sub2api_import_items_account_id"), table_name="sub2api_import_items")
    op.drop_table("sub2api_import_items")
    op.drop_index(op.f("ix_sub2api_import_batches_status"), table_name="sub2api_import_batches")
    op.drop_index(op.f("ix_sub2api_import_batches_retry_of_batch_id"), table_name="sub2api_import_batches")
    op.drop_index(op.f("ix_sub2api_import_batches_instance_id"), table_name="sub2api_import_batches")
    op.drop_index(op.f("ix_sub2api_import_batches_created_by"), table_name="sub2api_import_batches")
    op.drop_index(op.f("ix_sub2api_import_batches_batch_no"), table_name="sub2api_import_batches")
    op.drop_table("sub2api_import_batches")
