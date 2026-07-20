import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, File as UploadField, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.user import User
from app.services.data_portability import (
    BackupCommandError,
    BackupToolMissingError,
    export_backup,
    import_backup,
)

router = APIRouter(prefix="/api/system-maintenance", tags=["system-maintenance"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKUP_DIR = PROJECT_ROOT / "backups"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _upload_dir() -> Path:
    root = Path(settings.file_storage_dir)
    if not root.is_absolute():
        root = PROJECT_ROOT / "backend" / root
    return root.resolve()


def _alembic_head() -> str | None:
    try:
      config = Config(str(ALEMBIC_INI))
      script = ScriptDirectory.from_config(config)
      return script.get_current_head()
    except Exception:
      return None


def _safe_backup_path(filename: str) -> Path:
    if Path(filename).name != filename or not filename.endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup filename")
    path = (BACKUP_DIR / filename).resolve()
    root = BACKUP_DIR.resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup path")
    return path


@router.get("/status")
def get_status(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, object]:
    del current_user
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "alembic_head": _alembic_head(),
        "backup_dir": str(BACKUP_DIR),
        "upgrade_commands": {
            "docker": "./scripts/upgrade.sh docker",
            "native": "./scripts/upgrade.sh native",
        },
    }


@router.post("/backups")
def create_backup(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, object]:
    del current_user
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output_path = BACKUP_DIR / f"relay-station-ops-backup-{timestamp}.zip"
    try:
        path = export_backup(
            output_path=output_path,
            database_url=settings.database_url,
            upload_dir=_upload_dir(),
            app_field_encryption_key=settings.app_field_encryption_key,
        )
    except BackupToolMissingError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except BackupCommandError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {
        "filename": path.name,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "created_at": datetime.now(UTC).isoformat(),
    }


@router.get("/backups/{filename}/download")
def download_backup(
    filename: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> FileResponse:
    del current_user
    path = _safe_backup_path(filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.post("/import")
def import_backup_upload(
    upload: UploadFile = UploadField(...),
    force: bool = False,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    del current_user
    db.rollback()
    db.close()
    if not upload.filename or not upload.filename.endswith(".zip"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only backup zip files are supported")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = BACKUP_DIR / f"import-{uuid.uuid4()}.zip"
    try:
        with temp_path.open("wb") as output:
            shutil.copyfileobj(upload.file, output)
        try:
            import_backup(
                input_path=temp_path,
                database_url=settings.database_url,
                upload_dir=_upload_dir(),
                app_field_encryption_key=settings.app_field_encryption_key,
                force=force,
            )
        except BackupToolMissingError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except BackupCommandError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    finally:
        upload.file.close()
        temp_path.unlink(missing_ok=True)

    return {"status": "imported"}
