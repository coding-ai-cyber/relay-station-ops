"""add account items

Revision ID: 20260716_0004
Revises: 20260716_0003
Create Date: 2026-07-16 12:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0004"
down_revision: str | None = "20260716_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_items",
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("purchase_id", sa.UUID(), nullable=True),
        sa.Column("item_no", sa.String(length=120), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("plan_type", sa.String(length=50), nullable=True),
        sa.Column("remote_account_id", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("import_batch_no", sa.String(length=100), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_items_account_id"), "account_items", ["account_id"])
    op.create_index(op.f("ix_account_items_email"), "account_items", ["email"])
    op.create_index(op.f("ix_account_items_import_batch_no"), "account_items", ["import_batch_no"])
    op.create_index(op.f("ix_account_items_item_no"), "account_items", ["item_no"], unique=True)
    op.create_index(op.f("ix_account_items_platform"), "account_items", ["platform"])
    op.create_index(op.f("ix_account_items_purchase_id"), "account_items", ["purchase_id"])
    op.create_index(op.f("ix_account_items_remote_account_id"), "account_items", ["remote_account_id"])
    op.create_index(op.f("ix_account_items_status"), "account_items", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_account_items_status"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_remote_account_id"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_purchase_id"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_platform"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_item_no"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_import_batch_no"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_email"), table_name="account_items")
    op.drop_index(op.f("ix_account_items_account_id"), table_name="account_items")
    op.drop_table("account_items")
