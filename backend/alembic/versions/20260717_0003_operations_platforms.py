"""create operations platforms"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260717_0003"
down_revision: str | None = "20260717_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operations_platforms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("login_url", sa.Text(), nullable=True),
        sa.Column("login_account_encrypted", sa.Text(), nullable=True),
        sa.Column("login_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("bound_email", sa.String(length=200), nullable=True),
        sa.Column("bound_phone", sa.String(length=100), nullable=True),
        sa.Column("is_core", sa.Boolean(), nullable=False),
        sa.Column("has_expiry", sa.Boolean(), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("include_cost", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operations_platforms_name"), "operations_platforms", ["name"], unique=False)
    op.create_index(op.f("ix_operations_platforms_type"), "operations_platforms", ["type"], unique=False)
    op.create_index(op.f("ix_operations_platforms_is_core"), "operations_platforms", ["is_core"], unique=False)
    op.create_index(op.f("ix_operations_platforms_expired_at"), "operations_platforms", ["expired_at"], unique=False)
    op.create_index(op.f("ix_operations_platforms_status"), "operations_platforms", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operations_platforms_status"), table_name="operations_platforms")
    op.drop_index(op.f("ix_operations_platforms_expired_at"), table_name="operations_platforms")
    op.drop_index(op.f("ix_operations_platforms_is_core"), table_name="operations_platforms")
    op.drop_index(op.f("ix_operations_platforms_type"), table_name="operations_platforms")
    op.drop_index(op.f("ix_operations_platforms_name"), table_name="operations_platforms")
    op.drop_table("operations_platforms")
