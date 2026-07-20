"""add account item check status fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0002"
down_revision = "20260717_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("account_items", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("account_items", sa.Column("last_sub2api_status_code", sa.Integer(), nullable=True))
    op.add_column("account_items", sa.Column("last_sub2api_error_code", sa.String(length=100), nullable=True))
    op.add_column("account_items", sa.Column("last_sub2api_message", sa.Text(), nullable=True))
    op.add_column("account_items", sa.Column("first_seen_alive_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("account_items", sa.Column("last_seen_alive_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("account_items", sa.Column("first_abnormal_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("account_items", sa.Column("survival_seconds", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_account_items_last_checked_at"), "account_items", ["last_checked_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_account_items_last_checked_at"), table_name="account_items")
    op.drop_column("account_items", "survival_seconds")
    op.drop_column("account_items", "first_abnormal_at")
    op.drop_column("account_items", "last_seen_alive_at")
    op.drop_column("account_items", "first_seen_alive_at")
    op.drop_column("account_items", "last_sub2api_message")
    op.drop_column("account_items", "last_sub2api_error_code")
    op.drop_column("account_items", "last_sub2api_status_code")
    op.drop_column("account_items", "last_checked_at")
