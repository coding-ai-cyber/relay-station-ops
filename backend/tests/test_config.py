import unittest

from pydantic import ValidationError

from app.core.config import Settings


class SettingsSecurityTests(unittest.TestCase):
    def test_rejects_public_default_secrets(self):
        with self.assertRaises(ValidationError):
            Settings(
                app_secret_key="change-me",
                app_field_encryption_key="change-me-32-byte-base64-key",
                _env_file=None,
            )

    def test_accepts_explicit_strong_secrets(self):
        settings = Settings(
            app_secret_key="a" * 48,
            app_field_encryption_key="b" * 48,
            _env_file=None,
        )

        self.assertEqual(len(settings.app_secret_key), 48)
        self.assertEqual(len(settings.app_field_encryption_key), 48)


if __name__ == "__main__":
    unittest.main()
