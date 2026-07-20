"""add product name to cost items

Revision ID: 20260715_0001
Revises: 20260714_0001
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0001"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cost_items", sa.Column("product_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("cost_items", "product_name")
