import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File as UploadField, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.user import User
from app.schemas.file import FileRead

router = APIRouter(prefix="/api/files", tags=["files"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "upload"


def _storage_root() -> Path:
    root = Path(settings.file_storage_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    return root.resolve()


def _get_file_or_404(db: Session, file_id: uuid.UUID) -> File:
    file_record = db.get(File, file_id)
    if file_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return file_record


@router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
def upload_file(
    request: Request,
    upload: UploadFile = UploadField(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> File:
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only images and PDF files are supported",
        )

    file_id = uuid.uuid4()
    original_name = _safe_filename(upload.filename or "upload")
    storage_root = _storage_root()
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_path = storage_root / f"{file_id}_{original_name}"

    size = 0
    try:
        with storage_path.open("wb") as output:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    output.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File is larger than 20MB",
                    )
                output.write(chunk)
    finally:
        upload.file.close()

    file_record = File(
        id=file_id,
        original_name=original_name,
        storage_path=str(storage_path),
        content_type=upload.content_type,
        size_bytes=size,
        uploaded_by=current_user.id,
    )
    db.add(file_record)
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="upload_file",
            resource_type="file",
            resource_id=file_record.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={"original_name": original_name, "size_bytes": size},
        )
    )
    db.commit()
    db.refresh(file_record)
    return file_record


@router.get("/{file_id}", response_model=FileRead)
def get_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> File:
    del current_user
    return _get_file_or_404(db, file_id)


@router.get("/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    del current_user
    file_record = _get_file_or_404(db, file_id)
    storage_path = Path(file_record.storage_path).resolve()
    storage_root = _storage_root()

    if not storage_path.is_file() or storage_root not in storage_path.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file not found",
        )

    return FileResponse(
        storage_path,
        media_type=file_record.content_type,
        filename=file_record.original_name,
    )
