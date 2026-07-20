"""secure sub2api imports

Revision ID: 20260713_0004
Revises: 20260713_0003
Create Date: 2026-07-13
"""

from collections.abc import Sequence
import json

import sqlalchemy as sa
from alembic import op

from app.services.account_credentials import decrypt_raw_credentials, prepare_raw_payload

revision: str = "20260713_0004"
down_revision: str | None = "20260713_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("raw_credentials_encrypted", sa.Text(), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, raw_payload FROM accounts WHERE raw_payload IS NOT NULL")
    ).mappings()
    for row in rows:
        sanitized, encrypted = prepare_raw_payload(row["raw_payload"])
        connection.execute(
            sa.text(
                "UPDATE accounts "
                "SET raw_payload = CAST(:raw_payload AS jsonb), "
                "raw_credentials_encrypted = :encrypted "
                "WHERE id = :account_id"
            ),
            {
                "raw_payload": json.dumps(sanitized, ensure_ascii=False),
                "encrypted": encrypted,
                "account_id": row["id"],
            },
        )

    connection.execute(
        sa.text(
            "WITH ranked_retries AS ("
            "  SELECT id, retry_of_batch_id, "
            "         ROW_NUMBER() OVER ("
            "           PARTITION BY retry_of_batch_id ORDER BY created_at, id"
            "         ) AS retry_order, "
            "         LAG(id) OVER ("
            "           PARTITION BY retry_of_batch_id ORDER BY created_at, id"
            "         ) AS previous_retry_id "
            "  FROM sub2api_import_batches "
            "  WHERE retry_of_batch_id IS NOT NULL"
            ") "
            "UPDATE sub2api_import_batches AS batch "
            "SET retry_of_batch_id = ranked.previous_retry_id "
            "FROM ranked_retries AS ranked "
            "WHERE batch.id = ranked.id AND ranked.retry_order > 1"
        )
    )

    op.drop_index(
        op.f("ix_sub2api_import_batches_retry_of_batch_id"),
        table_name="sub2api_import_batches",
    )
    op.create_index(
        op.f("ix_sub2api_import_batches_retry_of_batch_id"),
        "sub2api_import_batches",
        ["retry_of_batch_id"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, raw_payload, raw_credentials_encrypted "
            "FROM accounts WHERE raw_credentials_encrypted IS NOT NULL"
        )
    ).mappings()
    for row in rows:
        credentials = decrypt_raw_credentials(row["raw_credentials_encrypted"])
        if credentials is None:
            continue
        raw_payload = row["raw_payload"] if isinstance(row["raw_payload"], dict) else {}
        raw_payload = {**raw_payload, "credentials": credentials}
        connection.execute(
            sa.text(
                "UPDATE accounts SET raw_payload = CAST(:raw_payload AS jsonb) "
                "WHERE id = :account_id"
            ),
            {
                "raw_payload": json.dumps(raw_payload, ensure_ascii=False),
                "account_id": row["id"],
            },
        )

    op.drop_index(
        op.f("ix_sub2api_import_batches_retry_of_batch_id"),
        table_name="sub2api_import_batches",
    )
    op.create_index(
        op.f("ix_sub2api_import_batches_retry_of_batch_id"),
        "sub2api_import_batches",
        ["retry_of_batch_id"],
        unique=False,
    )
    op.drop_column("accounts", "raw_credentials_encrypted")
