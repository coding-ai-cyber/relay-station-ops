import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import field_cipher
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.operations_platform import OperationsPlatform
from app.models.user import User
from app.schemas.operations_platform import (
    OperationsPlatformCreate,
    OperationsPlatformRead,
    OperationsPlatformSecretRead,
    OperationsPlatformUpdate,
)

router = APIRouter(prefix="/api/operations-platforms", tags=["operations-platforms"])


def _to_read(platform: OperationsPlatform) -> OperationsPlatformRead:
    return OperationsPlatformRead.model_validate(
        {
            **platform.__dict__,
            "has_login_account": bool(platform.login_account_encrypted),
            "has_login_secret": bool(platform.login_secret_encrypted),
        }
    )


def _get_or_404(db: Session, platform_id: uuid.UUID) -> OperationsPlatform:
    platform = db.get(OperationsPlatform, platform_id)
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operations platform not found")
    return platform


@router.get("", response_model=list[OperationsPlatformRead])
def list_operations_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_type: str | None = Query(default=None, alias="type"),
    platform_status: str | None = Query(default=None, alias="status"),
    is_core: bool | None = None,
    q: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[OperationsPlatformRead]:
    del current_user
    stmt = select(OperationsPlatform).order_by(OperationsPlatform.created_at.desc())
    if platform_type:
        stmt = stmt.where(OperationsPlatform.type == platform_type)
    if platform_status:
        stmt = stmt.where(OperationsPlatform.status == platform_status)
    if is_core is not None:
        stmt = stmt.where(OperationsPlatform.is_core == is_core)
    if q:
        stmt = stmt.where(OperationsPlatform.name.ilike(f"%{q}%"))
    return [_to_read(item) for item in db.scalars(stmt.offset(offset).limit(limit)).all()]


@router.post("", response_model=OperationsPlatformRead, status_code=status.HTTP_201_CREATED)
def create_operations_platform(
    payload: OperationsPlatformCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> OperationsPlatformRead:
    del current_user
    data = payload.model_dump(exclude={"login_account", "login_secret"})
    platform = OperationsPlatform(
        **data,
        login_account_encrypted=field_cipher.encrypt(payload.login_account),
        login_secret_encrypted=field_cipher.encrypt(payload.login_secret),
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return _to_read(platform)


@router.get("/{platform_id}", response_model=OperationsPlatformRead)
def get_operations_platform(
    platform_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OperationsPlatformRead:
    del current_user
    return _to_read(_get_or_404(db, platform_id))


@router.patch("/{platform_id}", response_model=OperationsPlatformRead)
def update_operations_platform(
    platform_id: uuid.UUID,
    payload: OperationsPlatformUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> OperationsPlatformRead:
    del current_user
    platform = _get_or_404(db, platform_id)
    data = payload.model_dump(exclude_unset=True)
    if "login_account" in data:
        platform.login_account_encrypted = field_cipher.encrypt(data.pop("login_account"))
    if "login_secret" in data:
        platform.login_secret_encrypted = field_cipher.encrypt(data.pop("login_secret"))
    for field_name, value in data.items():
        setattr(platform, field_name, value)
    db.commit()
    db.refresh(platform)
    return _to_read(platform)


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operations_platform(
    platform_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    del current_user
    platform = _get_or_404(db, platform_id)
    db.delete(platform)
    db.commit()


@router.post("/{platform_id}/reveal-secret", response_model=OperationsPlatformSecretRead)
def reveal_operations_platform_secret(
    platform_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> OperationsPlatformSecretRead:
    platform = _get_or_404(db, platform_id)
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="reveal_operations_platform_secret",
            resource_type="operations_platform",
            resource_id=platform.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={"platform_name": platform.name},
        )
    )
    db.commit()
    return OperationsPlatformSecretRead(
        id=platform.id,
        login_account=field_cipher.decrypt(platform.login_account_encrypted),
        login_secret=field_cipher.decrypt(platform.login_secret_encrypted),
    )
