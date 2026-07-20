import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDED_TABLES = ["audit_logs"]
METADATA_NAME = "metadata.json"
DATABASE_DUMP_NAME = "database.dump"
UPLOADS_PREFIX = "uploads/"


class BackupToolMissingError(RuntimeError):
    pass


class BackupCommandError(RuntimeError):
    pass


def key_fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _libpq_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1).replace(
        "postgresql+psycopg2://",
        "postgresql://",
        1,
    )


def _write_uploads(archive: ZipFile, upload_dir: Path) -> None:
    if not upload_dir.exists():
        return
    for path in sorted(upload_dir.rglob("*")):
        if path.is_file():
            archive.write(path, UPLOADS_PREFIX + path.relative_to(upload_dir).as_posix())


def _restore_uploads(archive: ZipFile, upload_dir: Path) -> None:
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    for name in archive.namelist():
        if not name.startswith(UPLOADS_PREFIX) or name.endswith("/"):
            continue
        relative = Path(name.removeprefix(UPLOADS_PREFIX))
        target = (upload_dir / relative).resolve()
        root = upload_dir.resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"Unsafe upload archive path: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(name))


def _metadata(app_field_encryption_key: str) -> dict[str, object]:
    return {
        "format": "sub2api-ops-backup",
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "excluded_tables": EXCLUDED_TABLES,
        "app_field_encryption_key_fingerprint": key_fingerprint(app_field_encryption_key),
    }


def export_backup(
    output_path: Path,
    database_url: str,
    upload_dir: Path,
    app_field_encryption_key: str,
) -> Path:
    output_path = output_path.resolve()
    upload_root = upload_dir.resolve()
    if output_path == upload_root or upload_root in output_path.parents:
        raise ValueError("Backup output path must be outside the upload directory.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        dump_path = Path(tmp) / DATABASE_DUMP_NAME
        command = [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--exclude-table-data=audit_logs",
            "--file",
            str(dump_path),
            _libpq_database_url(database_url),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise BackupToolMissingError("pg_dump is not installed or not available in PATH.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise BackupCommandError(f"pg_dump failed: {detail}") from exc
        if not dump_path.exists():
            dump_path.write_bytes(b"")

        with ZipFile(output_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr(METADATA_NAME, json.dumps(_metadata(app_field_encryption_key), ensure_ascii=False, indent=2))
            archive.write(dump_path, DATABASE_DUMP_NAME)
            _write_uploads(archive, upload_dir)
    return output_path


def import_backup(
    input_path: Path,
    database_url: str,
    upload_dir: Path,
    app_field_encryption_key: str,
    force: bool = False,
) -> None:
    input_path = input_path.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        dump_path = Path(tmp) / DATABASE_DUMP_NAME
        with ZipFile(input_path) as archive:
            metadata = json.loads(archive.read(METADATA_NAME).decode("utf-8"))
            expected = metadata.get("app_field_encryption_key_fingerprint")
            actual = key_fingerprint(app_field_encryption_key)
            if expected != actual and not force:
                raise ValueError(
                    "Backup APP_FIELD_ENCRYPTION_KEY fingerprint does not match the current environment. "
                    "Use the original key or pass --force if you accept encrypted fields may be unreadable."
                )
            dump_path.write_bytes(archive.read(DATABASE_DUMP_NAME))
            _restore_uploads(archive, upload_dir)

        command = [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            _libpq_database_url(database_url),
            str(dump_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise BackupToolMissingError("pg_restore is not installed or not available in PATH.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise BackupCommandError(f"pg_restore failed: {detail}") from exc


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL")
    parser.add_argument("--upload-dir", default=None, help="Override FILE_STORAGE_DIR")
    parser.add_argument("--field-encryption-key", default=None, help="Override APP_FIELD_ENCRYPTION_KEY")
