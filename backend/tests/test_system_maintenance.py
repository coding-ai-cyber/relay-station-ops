import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

from app.core.enums import UserRole


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class SystemMaintenanceRouteTests(unittest.TestCase):
    def test_routes_are_admin_only(self):
        from app.api.routes.system_maintenance import router

        protected = {
            ("/api/system-maintenance/status", "GET"),
            ("/api/system-maintenance/backups", "POST"),
            ("/api/system-maintenance/backups/{filename}/download", "GET"),
            ("/api/system-maintenance/import", "POST"),
        }
        routes = [
            route
            for route in router.routes
            if (route.path, next(iter(route.methods))) in protected
        ]

        self.assertEqual(len(routes), len(protected))
        for route in routes:
            role_dependency = next(
                dependency
                for dependency in route.dependant.dependencies
                if dependency.name == "current_user"
            )
            allowed_roles = inspect.getclosurevars(role_dependency.call).nonlocals["allowed_roles"]
            self.assertEqual(allowed_roles, {UserRole.ADMIN.value})

    def test_create_backup_uses_portability_service(self):
        from app.api.routes import system_maintenance

        with tempfile.TemporaryDirectory() as tmp:
            system_maintenance.BACKUP_DIR = Path(tmp)
            expected = Path(tmp) / "backup.zip"
            with patch(
                "app.api.routes.system_maintenance.export_backup",
                return_value=expected,
            ) as exporter:
                result = system_maintenance.create_backup(current_user=object())

        exporter.assert_called_once_with(
            output_path=ANY,
            database_url=ANY,
            upload_dir=ANY,
            app_field_encryption_key=ANY,
        )
        self.assertEqual(result["filename"], "backup.zip")

    def test_create_backup_reports_missing_pg_dump(self):
        from fastapi import HTTPException

        from app.api.routes import system_maintenance
        from app.services.data_portability import BackupToolMissingError

        with tempfile.TemporaryDirectory() as tmp:
            system_maintenance.BACKUP_DIR = Path(tmp)
            with patch(
                "app.api.routes.system_maintenance.export_backup",
                side_effect=BackupToolMissingError("pg_dump is not installed or not available in PATH."),
            ):
                with self.assertRaises(HTTPException) as raised:
                    system_maintenance.create_backup(current_user=object())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("pg_dump", raised.exception.detail)

    def test_import_backup_upload_uses_portability_service(self):
        from app.api.routes import system_maintenance

        class Upload:
            filename = "backup.zip"

            def __init__(self) -> None:
                self.file = self
                self.closed = False

            def read(self, size: int = -1) -> bytes:
                del size
                if self.closed:
                    return b""
                self.closed = True
                return b"zip"

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            system_maintenance.BACKUP_DIR = Path(tmp)
            with patch("app.api.routes.system_maintenance.import_backup") as importer:
                db = FakeSession()
                result = system_maintenance.import_backup_upload(
                    upload=Upload(),
                    force=True,
                    current_user=object(),
                    db=db,
                )

        self.assertTrue(db.rolled_back)
        self.assertTrue(db.closed)

        importer.assert_called_once()
        self.assertTrue(importer.call_args.kwargs["force"])
        self.assertEqual(result["status"], "imported")

    def test_import_backup_upload_reports_key_mismatch(self):
        from fastapi import HTTPException

        from app.api.routes import system_maintenance

        class Upload:
            filename = "backup.zip"

            def __init__(self) -> None:
                self.file = self
                self.closed = False

            def read(self, size: int = -1) -> bytes:
                del size
                if self.closed:
                    return b""
                self.closed = True
                return b"zip"

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            system_maintenance.BACKUP_DIR = Path(tmp)
            with patch(
                "app.api.routes.system_maintenance.import_backup",
                side_effect=ValueError("Backup APP_FIELD_ENCRYPTION_KEY fingerprint does not match"),
            ):
                with self.assertRaises(HTTPException) as raised:
                    system_maintenance.import_backup_upload(
                        upload=Upload(), current_user=object(), db=FakeSession()
                    )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("APP_FIELD_ENCRYPTION_KEY", raised.exception.detail)

    def test_import_backup_upload_reports_restore_failure(self):
        from fastapi import HTTPException

        from app.api.routes import system_maintenance
        from app.services.data_portability import BackupCommandError

        class Upload:
            filename = "backup.zip"

            def __init__(self) -> None:
                self.file = self
                self.closed = False

            def read(self, size: int = -1) -> bytes:
                del size
                if self.closed:
                    return b""
                self.closed = True
                return b"zip"

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            system_maintenance.BACKUP_DIR = Path(tmp)
            with patch(
                "app.api.routes.system_maintenance.import_backup",
                side_effect=BackupCommandError("pg_restore failed: restore failed"),
            ):
                with self.assertRaises(HTTPException) as raised:
                    system_maintenance.import_backup_upload(
                        upload=Upload(), current_user=object(), db=FakeSession()
                    )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertIn("pg_restore failed", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
