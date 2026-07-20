"""account sub2api checks

Revision ID: 20260713_0001
Revises: 20260711_0001
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0001"
down_revision: str | None = "20260711_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("authorized_email", sa.String(length=200), nullable=True))
    op.add_column("accounts", sa.Column("sub2api_account_id", sa.String(length=200), nullable=True))
    op.add_column("accounts", sa.Column("sub2api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("import_file_id", sa.UUID(), nullable=True))
    op.add_column("accounts", sa.Column("import_batch_no", sa.String(length=100), nullable=True))
    op.add_column("accounts", sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("accounts", sa.Column("first_seen_alive_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("accounts", sa.Column("last_seen_alive_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("accounts", sa.Column("first_abnormal_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("accounts", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("accounts", sa.Column("last_sub2api_status_code", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("last_sub2api_error_code", sa.String(length=100), nullable=True))
    op.add_column("accounts", sa.Column("last_sub2api_message", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("survival_seconds", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_accounts_import_batch_no"), "accounts", ["import_batch_no"], unique=False)
    op.create_index(op.f("ix_accounts_import_file_id"), "accounts", ["import_file_id"], unique=False)
    op.create_index(op.f("ix_accounts_last_checked_at"), "accounts", ["last_checked_at"], unique=False)
    op.create_index(op.f("ix_accounts_sub2api_account_id"), "accounts", ["sub2api_account_id"], unique=False)
    op.create_foreign_key(
        "fk_accounts_import_file_id_files",
        "accounts",
        "files",
        ["import_file_id"],
        ["id"],
    )

    op.create_table(
        "account_check_batches",
        sa.Column("batch_no", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("checked_by", sa.UUID(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("alive_count", sa.Integer(), nullable=False),
        sa.Column("abnormal_count", sa.Integer(), nullable=False),
        sa.Column("status_401_count", sa.Integer(), nullable=False),
        sa.Column("status_403_count", sa.Integer(), nullable=False),
        sa.Column("status_429_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_check_batches_batch_no"), "account_check_batches", ["batch_no"], unique=True)
    op.create_index(op.f("ix_account_check_batches_checked_by"), "account_check_batches", ["checked_by"], unique=False)
    op.create_index(op.f("ix_account_check_batches_source"), "account_check_batches", ["source"], unique=False)

    op.create_table(
        "account_check_records",
        sa.Column("batch_id", sa.UUID(), nullable=True),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("sub2api_status", sa.String(length=100), nullable=True),
        sa.Column("is_alive", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("survived_seconds", sa.Integer(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["account_check_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_check_records_account_id"), "account_check_records", ["account_id"], unique=False)
    op.create_index(op.f("ix_account_check_records_batch_id"), "account_check_records", ["batch_id"], unique=False)
    op.create_index(op.f("ix_account_check_records_checked_at"), "account_check_records", ["checked_at"], unique=False)
    op.create_index(op.f("ix_account_check_records_error_code"), "account_check_records", ["error_code"], unique=False)
    op.create_index(op.f("ix_account_check_records_http_status"), "account_check_records", ["http_status"], unique=False)
    op.create_index(op.f("ix_account_check_records_is_alive"), "account_check_records", ["is_alive"], unique=False)
    op.create_index(op.f("ix_account_check_records_sub2api_status"), "account_check_records", ["sub2api_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_account_check_records_sub2api_status"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_is_alive"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_http_status"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_error_code"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_checked_at"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_batch_id"), table_name="account_check_records")
    op.drop_index(op.f("ix_account_check_records_account_id"), table_name="account_check_records")
    op.drop_table("account_check_records")
    op.drop_index(op.f("ix_account_check_batches_source"), table_name="account_check_batches")
    op.drop_index(op.f("ix_account_check_batches_checked_by"), table_name="account_check_batches")
    op.drop_index(op.f("ix_account_check_batches_batch_no"), table_name="account_check_batches")
    op.drop_table("account_check_batches")
    op.drop_constraint("fk_accounts_import_file_id_files", "accounts", type_="foreignkey")
    op.drop_index(op.f("ix_accounts_sub2api_account_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_last_checked_at"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_import_file_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_import_batch_no"), table_name="accounts")
    op.drop_column("accounts", "survival_seconds")
    op.drop_column("accounts", "last_sub2api_message")
    op.drop_column("accounts", "last_sub2api_error_code")
    op.drop_column("accounts", "last_sub2api_status_code")
    op.drop_column("accounts", "last_checked_at")
    op.drop_column("accounts", "first_abnormal_at")
    op.drop_column("accounts", "last_seen_alive_at")
    op.drop_column("accounts", "first_seen_alive_at")
    op.drop_column("accounts", "raw_payload")
    op.drop_column("accounts", "import_batch_no")
    op.drop_column("accounts", "import_file_id")
    op.drop_column("accounts", "sub2api_key_encrypted")
    op.drop_column("accounts", "sub2api_account_id")
    op.drop_column("accounts", "authorized_email")
