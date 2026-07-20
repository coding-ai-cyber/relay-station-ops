"""account sub2api instance link

Revision ID: 20260714_0001
Revises: 20260713_0004
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0001"
down_revision: str | None = "20260713_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("sub2api_instance_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_accounts_sub2api_instance_id"),
        "accounts",
        ["sub2api_instance_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_accounts_sub2api_instance_id_sub2api_instances",
        "accounts",
        "sub2api_instances",
        ["sub2api_instance_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_accounts_sub2api_instance_id_sub2api_instances",
        "accounts",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_accounts_sub2api_instance_id"), table_name="accounts")
    op.drop_column("accounts", "sub2api_instance_id")
