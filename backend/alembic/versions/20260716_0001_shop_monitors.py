"""add shop monitors

Revision ID: 20260716_0001
Revises: 20260715_0001
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0001"
down_revision: str | None = "20260715_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shop_monitors",
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("shop_url", sa.Text(), nullable=False),
        sa.Column("shop_token", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=50), nullable=False),
        sa.Column("last_sync_message", sa.Text(), nullable=True),
        sa.Column("raw_shop_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shop_monitors_enabled"), "shop_monitors", ["enabled"], unique=False)
    op.create_index(op.f("ix_shop_monitors_platform"), "shop_monitors", ["platform"], unique=False)
    op.create_index(op.f("ix_shop_monitors_shop_token"), "shop_monitors", ["shop_token"], unique=True)
    op.create_index(op.f("ix_shop_monitors_supplier_id"), "shop_monitors", ["supplier_id"], unique=False)
    op.create_index(
        op.f("ix_shop_monitors_last_sync_status"),
        "shop_monitors",
        ["last_sync_status"],
        unique=False,
    )

    op.create_table(
        "shop_products",
        sa.Column("monitor_id", sa.UUID(), nullable=False),
        sa.Column("external_product_id", sa.String(length=100), nullable=False),
        sa.Column("goods_type", sa.String(length=50), nullable=False),
        sa.Column("category_id", sa.String(length=100), nullable=True),
        sa.Column("category_name", sa.String(length=200), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("market_price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("is_out_of_stock", sa.Boolean(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["monitor_id"], ["shop_monitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitor_id", "external_product_id", name="uq_shop_products_monitor_external"),
    )
    op.create_index(op.f("ix_shop_products_category_id"), "shop_products", ["category_id"], unique=False)
    op.create_index(op.f("ix_shop_products_external_product_id"), "shop_products", ["external_product_id"], unique=False)
    op.create_index(op.f("ix_shop_products_goods_type"), "shop_products", ["goods_type"], unique=False)
    op.create_index(op.f("ix_shop_products_is_out_of_stock"), "shop_products", ["is_out_of_stock"], unique=False)
    op.create_index(op.f("ix_shop_products_monitor_id"), "shop_products", ["monitor_id"], unique=False)
    op.create_index(op.f("ix_shop_products_name"), "shop_products", ["name"], unique=False)
    op.create_index(op.f("ix_shop_products_stock_count"), "shop_products", ["stock_count"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shop_products_stock_count"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_name"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_monitor_id"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_is_out_of_stock"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_goods_type"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_external_product_id"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_category_id"), table_name="shop_products")
    op.drop_table("shop_products")
    op.drop_index(op.f("ix_shop_monitors_last_sync_status"), table_name="shop_monitors")
    op.drop_index(op.f("ix_shop_monitors_supplier_id"), table_name="shop_monitors")
    op.drop_index(op.f("ix_shop_monitors_shop_token"), table_name="shop_monitors")
    op.drop_index(op.f("ix_shop_monitors_platform"), table_name="shop_monitors")
    op.drop_index(op.f("ix_shop_monitors_enabled"), table_name="shop_monitors")
    op.drop_table("shop_monitors")
