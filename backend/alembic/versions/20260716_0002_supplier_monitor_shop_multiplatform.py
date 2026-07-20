"""supplier monitor shop and multiplatform shop monitors

Revision ID: 20260716_0002
Revises: 20260716_0001
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0002"
down_revision: str | None = "20260716_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column("monitor_shop", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.drop_index(op.f("ix_shop_monitors_shop_token"), table_name="shop_monitors")
    op.create_index(
        op.f("ix_shop_monitors_shop_token"),
        "shop_monitors",
        ["shop_token"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_shop_monitors_platform_token",
        "shop_monitors",
        ["platform", "shop_token"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_shop_monitors_platform_token",
        "shop_monitors",
        type_="unique",
    )
    op.drop_index(op.f("ix_shop_monitors_shop_token"), table_name="shop_monitors")
    op.create_index(
        op.f("ix_shop_monitors_shop_token"),
        "shop_monitors",
        ["shop_token"],
        unique=True,
    )
    op.drop_column("suppliers", "monitor_shop")
