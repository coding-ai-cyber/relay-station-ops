"""add shop product standard categories

Revision ID: 20260716_0003
Revises: 20260716_0002
Create Date: 2026-07-16 10:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shop_products", sa.Column("standard_category_key", sa.String(length=200), nullable=True))
    op.add_column("shop_products", sa.Column("standard_category_name", sa.String(length=200), nullable=True))
    op.add_column(
        "shop_products",
        sa.Column("category_duplicate_status", sa.String(length=50), nullable=False, server_default="unique"),
    )
    op.create_index(op.f("ix_shop_products_standard_category_key"), "shop_products", ["standard_category_key"])
    op.create_index(op.f("ix_shop_products_standard_category_name"), "shop_products", ["standard_category_name"])
    op.create_index(op.f("ix_shop_products_category_duplicate_status"), "shop_products", ["category_duplicate_status"])
    op.execute(
        """
        WITH normalized AS (
            SELECT
                id,
                category_id,
                NULLIF(lower(trim(category_name)), '') AS standard_key,
                COALESCE(NULLIF(trim(category_name), ''), '未分类') AS display_name
            FROM shop_products
        ),
        canonical_name AS (
            SELECT DISTINCT ON (standard_key)
                standard_key,
                category_id AS primary_category_id,
                display_name AS standard_name
            FROM normalized
            ORDER BY standard_key, category_id NULLS LAST, display_name
        ),
        canonical AS (
            SELECT
                normalized.standard_key,
                canonical_name.standard_name,
                canonical_name.primary_category_id,
                COUNT(DISTINCT category_id) AS category_id_count
            FROM normalized
            JOIN canonical_name ON normalized.standard_key IS NOT DISTINCT FROM canonical_name.standard_key
            GROUP BY normalized.standard_key, canonical_name.standard_name, canonical_name.primary_category_id
        )
        UPDATE shop_products AS product
        SET
            standard_category_key = normalized.standard_key,
            standard_category_name = canonical.standard_name,
            category_duplicate_status = CASE
                WHEN canonical.category_id_count > 1
                    AND product.category_id IS DISTINCT FROM canonical.primary_category_id
                    THEN 'auto_merged'
                ELSE 'unique'
            END
        FROM normalized
        JOIN canonical ON normalized.standard_key IS NOT DISTINCT FROM canonical.standard_key
        WHERE product.id = normalized.id
        """
    )
    op.alter_column("shop_products", "category_duplicate_status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_shop_products_category_duplicate_status"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_standard_category_name"), table_name="shop_products")
    op.drop_index(op.f("ix_shop_products_standard_category_key"), table_name="shop_products")
    op.drop_column("shop_products", "category_duplicate_status")
    op.drop_column("shop_products", "standard_category_name")
    op.drop_column("shop_products", "standard_category_key")
