"""add supplier preferred product tags

Revision ID: 20260717_0001
Revises: 20260716_0004
Create Date: 2026-07-17 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0001"
down_revision: str | None = "20260716_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column(
            "preferred_product_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("suppliers", "preferred_product_tags", server_default=None)


def downgrade() -> None:
    op.drop_column("suppliers", "preferred_product_tags")
