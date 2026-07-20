import unittest
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.api.routes.accounts import to_account_read
from app.core.security import field_cipher
from app.models.account import Account
from app.schemas.sub2api_import import Sub2APIImportCreate
from app.services.account_credentials import decrypt_raw_credentials, prepare_raw_payload


class AccountCredentialStorageTests(unittest.TestCase):
    def test_encrypts_credentials_and_redacts_raw_payload(self):
        sanitized, encrypted = prepare_raw_payload(
            {
                "platform": "openai",
                "credentials": {"access_token": "access", "refresh_token": "refresh"},
            }
        )

        self.assertEqual(sanitized["credentials"], "[REDACTED]")
        self.assertNotIn("access", str(sanitized))
        self.assertEqual(
            decrypt_raw_credentials(encrypted),
            {"access_token": "access", "refresh_token": "refresh"},
        )

    def test_preserves_existing_encrypted_credentials_for_redacted_update(self):
        existing = field_cipher.encrypt('{"api_key":"secret"}')

        sanitized, encrypted = prepare_raw_payload(
            {"platform": "openai", "credentials": "[REDACTED]"},
            existing_encrypted=existing,
        )

        self.assertEqual(sanitized["credentials"], "[REDACTED]")
        self.assertEqual(encrypted, existing)

    def test_encrypts_flat_oauth_credentials_before_redacting_them(self):
        sanitized, encrypted = prepare_raw_payload(
            {
                "platform": "openai",
                "type": "oauth",
                "access_token": "access",
                "refresh_token": "refresh",
            }
        )

        self.assertEqual(sanitized["access_token"], "[REDACTED]")
        self.assertEqual(sanitized["refresh_token"], "[REDACTED]")
        self.assertEqual(
            decrypt_raw_credentials(encrypted),
            {"access_token": "access", "refresh_token": "refresh"},
        )

    def test_account_read_uses_encrypted_column_for_credential_readiness(self):
        now = datetime.now(UTC)
        account = Account(
            id=uuid.uuid4(),
            account_no="ACC-001",
            account_type="OpenAI",
            raw_payload={"platform": "openai", "credentials": "[REDACTED]"},
            raw_credentials_encrypted=field_cipher.encrypt('{"api_key":"secret"}'),
            status="pending_test",
            participate_operation=False,
            include_real_cost=False,
        )
        account.created_at = now
        account.updated_at = now

        result = to_account_read(account)

        self.assertTrue(result.has_raw_credentials)
        self.assertEqual(result.raw_payload["credentials"], "[REDACTED]")


class Sub2APIImportCreateTests(unittest.TestCase):
    def test_accepts_server_side_select_all_without_account_ids(self):
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            select_all=True,
            group_ids=[1],
        )

        self.assertTrue(payload.select_all)
        self.assertEqual(payload.account_ids, [])

    def test_requires_account_ids_when_select_all_is_false(self):
        with self.assertRaises(ValidationError):
            Sub2APIImportCreate(instance_id=uuid.uuid4(), group_ids=[1])

    def test_rejects_account_ids_together_with_select_all(self):
        with self.assertRaises(ValidationError):
            Sub2APIImportCreate(
                instance_id=uuid.uuid4(),
                select_all=True,
                account_ids=[uuid.uuid4()],
                group_ids=[1],
            )


if __name__ == "__main__":
    unittest.main()
