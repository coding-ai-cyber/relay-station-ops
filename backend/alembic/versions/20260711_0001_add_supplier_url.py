"""add supplier url

Revision ID: 20260711_0001
Revises: 8966c628c017
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0001"
down_revision: str | None = "8966c628c017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "url")
