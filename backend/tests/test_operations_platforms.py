import unittest

from app.core.security import field_cipher
from app.db.session import SessionLocal
from app.models.operations_platform import OperationsPlatform


class OperationsPlatformPersistenceTests(unittest.TestCase):
    def test_insert_uses_timestamp_defaults(self):
        with SessionLocal() as db:
            platform = OperationsPlatform(
                name="pytest operations platform",
                type="email",
                login_url="https://example.com",
                login_account_encrypted=field_cipher.encrypt("user@example.com"),
                login_secret_encrypted=field_cipher.encrypt("secret"),
                is_core=False,
                status="active",
            )
            db.add(platform)
            db.commit()
            db.refresh(platform)

            try:
                self.assertIsNotNone(platform.created_at)
                self.assertIsNotNone(platform.updated_at)
            finally:
                db.delete(platform)
                db.commit()


if __name__ == "__main__":
    unittest.main()
