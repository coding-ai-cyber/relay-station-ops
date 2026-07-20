import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


class DataPortabilityTests(unittest.TestCase):
    def test_export_excludes_audit_logs_and_packages_uploads(self):
        from app.services.data_portability import export_backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            (upload_dir / "voucher.txt").write_text("voucher", encoding="utf-8")
            output = root / "backup.zip"

            with patch("app.services.data_portability.subprocess.run") as run:
                result = export_backup(
                    output_path=output,
                    database_url="postgresql://user:pass@localhost:5432/db",
                    upload_dir=upload_dir,
                    app_field_encryption_key="field-key-12345678901234567890",
                )

            self.assertEqual(result, output.resolve())
            command = run.call_args.args[0]
            self.assertIn("--exclude-table-data=audit_logs", command)
            self.assertIn("--format=custom", command)
            self.assertTrue(output.exists())

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("metadata.json", names)
                self.assertIn("database.dump", names)
                self.assertIn("uploads/voucher.txt", names)
                metadata = json.loads(archive.read("metadata.json").decode("utf-8"))

            self.assertEqual(metadata["excluded_tables"], ["audit_logs"])
            self.assertEqual(metadata["app_field_encryption_key_fingerprint"][:7], "sha256:")

    def test_export_converts_sqlalchemy_driver_url_for_pg_dump(self):
        from app.services.data_portability import export_backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "backup.zip"

            with patch("app.services.data_portability.subprocess.run") as run:
                export_backup(
                    output_path=output,
                    database_url="postgresql+psycopg://user:pass@postgres:5432/db",
                    upload_dir=root / "uploads",
                    app_field_encryption_key="field-key-12345678901234567890",
                )

            command = run.call_args.args[0]
            self.assertEqual(command[-1], "postgresql://user:pass@postgres:5432/db")

    def test_export_reports_missing_pg_dump(self):
        from app.services.data_portability import BackupToolMissingError, export_backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "backup.zip"

            with patch("app.services.data_portability.subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaises(BackupToolMissingError) as raised:
                    export_backup(
                        output_path=output,
                        database_url="postgresql://user:pass@localhost:5432/db",
                        upload_dir=root / "uploads",
                        app_field_encryption_key="field-key-12345678901234567890",
                    )

            self.assertIn("pg_dump", str(raised.exception))

    def test_import_rejects_mismatched_encryption_key_without_force(self):
        from app.services.data_portability import import_backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "backup.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps(
                        {
                            "app_field_encryption_key_fingerprint": "sha256:not-the-current-key",
                            "excluded_tables": ["audit_logs"],
                        }
                    ),
                )
                archive.writestr("database.dump", b"dump")

            with self.assertRaises(ValueError) as raised:
                import_backup(
                    input_path=backup,
                    database_url="postgresql://user:pass@localhost:5432/db",
                    upload_dir=root / "uploads",
                    app_field_encryption_key="field-key-12345678901234567890",
                )

            self.assertIn("APP_FIELD_ENCRYPTION_KEY", str(raised.exception))

    def test_import_restores_database_and_uploads_when_key_matches(self):
        from app.services.data_portability import import_backup, key_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = "field-key-12345678901234567890"
            backup = root / "backup.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps(
                        {
                            "app_field_encryption_key_fingerprint": key_fingerprint(key),
                            "excluded_tables": ["audit_logs"],
                        }
                    ),
                )
                archive.writestr("database.dump", b"dump")
                archive.writestr("uploads/voucher.txt", "voucher")

            with patch("app.services.data_portability.subprocess.run") as run:
                import_backup(
                    input_path=backup,
                    database_url="postgresql://user:pass@localhost:5432/db",
                    upload_dir=root / "uploads",
                    app_field_encryption_key=key,
                )

            command = run.call_args.args[0]
            self.assertIn("--clean", command)
            self.assertIn("--if-exists", command)
            self.assertEqual(command[-2], "postgresql://user:pass@localhost:5432/db")
            self.assertEqual((root / "uploads" / "voucher.txt").read_text(encoding="utf-8"), "voucher")

    def test_import_clears_upload_contents_without_removing_upload_root(self):
        from app.services.data_portability import import_backup, key_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = "field-key-12345678901234567890"
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            (upload_dir / "old.txt").write_text("old", encoding="utf-8")
            backup = root / "backup.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps({"app_field_encryption_key_fingerprint": key_fingerprint(key)}),
                )
                archive.writestr("database.dump", b"dump")
                archive.writestr("uploads/new.txt", "new")

            def fail_if_upload_root_removed(path, *args, **kwargs):
                if Path(path) == upload_dir:
                    raise OSError("upload root must not be removed")
                return None

            with patch("app.services.data_portability.subprocess.run"), patch(
                "app.services.data_portability.shutil.rmtree",
                side_effect=fail_if_upload_root_removed,
            ):
                import_backup(
                    input_path=backup,
                    database_url="postgresql://user:pass@localhost:5432/db",
                    upload_dir=upload_dir,
                    app_field_encryption_key=key,
                )

            self.assertTrue(upload_dir.exists())
            self.assertFalse((upload_dir / "old.txt").exists())
            self.assertEqual((upload_dir / "new.txt").read_text(encoding="utf-8"), "new")

    def test_import_ignores_pg17_transaction_timeout_warning(self):
        import subprocess

        from app.services.data_portability import import_backup, key_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = "field-key-12345678901234567890"
            backup = root / "backup.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps({"app_field_encryption_key_fingerprint": key_fingerprint(key)}),
                )
                archive.writestr("database.dump", b"dump")

            stderr = (
                'pg_restore: error: could not execute query: ERROR: unrecognized configuration parameter \"transaction_timeout\"\n'
                'Command was: SET transaction_timeout = 0;\n'
                'pg_restore: warning: errors ignored on restore: 1'
            )
            error = subprocess.CalledProcessError(1, ["pg_restore"], stderr=stderr)
            with patch("app.services.data_portability.subprocess.run", side_effect=error):
                import_backup(
                    input_path=backup,
                    database_url="postgresql://user:pass@localhost:5432/db",
                    upload_dir=root / "uploads",
                    app_field_encryption_key=key,
                )

    def test_import_reports_pg_restore_failure(self):
        import subprocess

        from app.services.data_portability import BackupCommandError, import_backup, key_fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = "field-key-12345678901234567890"
            backup = root / "backup.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps({"app_field_encryption_key_fingerprint": key_fingerprint(key)}),
                )
                archive.writestr("database.dump", b"dump")

            error = subprocess.CalledProcessError(1, ["pg_restore"], stderr="restore failed")
            with patch("app.services.data_portability.subprocess.run", side_effect=error):
                with self.assertRaises(BackupCommandError) as raised:
                    import_backup(
                        input_path=backup,
                        database_url="postgresql://user:pass@localhost:5432/db",
                        upload_dir=root / "uploads",
                        app_field_encryption_key=key,
                    )

            self.assertIn("restore failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
