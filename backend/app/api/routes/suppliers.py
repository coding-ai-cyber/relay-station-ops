import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import field_cipher
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.shop_monitor import ShopMonitor
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate,
    SupplierRead,
    SupplierSecretRead,
    SupplierUpdate,
)
from app.services.link_shop_monitor import parse_shop_reference

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _to_supplier_read(supplier: Supplier) -> SupplierRead:
    return SupplierRead.model_validate(
        {
            **supplier.__dict__,
            "has_login_account": bool(supplier.login_account),
            "has_login_secret": bool(supplier.login_secret_encrypted),
        }
    )


def _get_supplier_or_404(db: Session, supplier_id: uuid.UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return supplier


def sync_supplier_shop_monitor(db: Session, supplier: Supplier) -> None:
    if supplier.type != "account" or not supplier.monitor_shop or not supplier.login_url:
        return
    try:
        platform, token = parse_shop_reference(supplier.login_url)
    except ValueError:
        return

    monitor = db.scalar(
        select(ShopMonitor).where(
            ShopMonitor.platform == platform.platform,
            ShopMonitor.shop_token == token,
        )
    )
    if monitor is None:
        db.add(
            ShopMonitor(
                supplier_id=supplier.id,
                name=supplier.name,
                shop_url=supplier.login_url,
                shop_token=token,
                platform=platform.platform,
                enabled=True,
            )
        )
        return

    monitor.supplier_id = supplier.id
    monitor.name = supplier.name
    monitor.shop_url = supplier.login_url
    monitor.enabled = True


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    supplier_type: str | None = Query(default=None, alias="type"),
    supplier_status: str | None = Query(default=None, alias="status"),
    continue_cooperation: bool | None = None,
    q: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SupplierRead]:
    del current_user
    stmt = select(Supplier).order_by(Supplier.created_at.desc()).offset(offset).limit(limit)

    if supplier_type:
        stmt = stmt.where(Supplier.type == supplier_type)
    if supplier_status:
        stmt = stmt.where(Supplier.status == supplier_status)
    if continue_cooperation is not None:
        stmt = stmt.where(Supplier.continue_cooperation == continue_cooperation)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))

    return [_to_supplier_read(item) for item in db.scalars(stmt).all()]


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> SupplierRead:
    del current_user
    data = payload.model_dump(exclude={"login_account", "login_secret"})
    supplier = Supplier(
        **data,
        login_account=field_cipher.encrypt(payload.login_account),
        login_secret_encrypted=field_cipher.encrypt(payload.login_secret),
    )
    db.add(supplier)
    sync_supplier_shop_monitor(db, supplier)
    db.commit()
    db.refresh(supplier)
    return _to_supplier_read(supplier)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SupplierRead:
    del current_user
    supplier = _get_supplier_or_404(db, supplier_id)
    return _to_supplier_read(supplier)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> SupplierRead:
    del current_user
    supplier = _get_supplier_or_404(db, supplier_id)
    data = payload.model_dump(exclude_unset=True)

    if "login_account" in data:
        supplier.login_account = field_cipher.encrypt(data.pop("login_account"))
    if "login_secret" in data:
        supplier.login_secret_encrypted = field_cipher.encrypt(data.pop("login_secret"))

    for field_name, value in data.items():
        setattr(supplier, field_name, value)

    sync_supplier_shop_monitor(db, supplier)
    db.commit()
    db.refresh(supplier)
    return _to_supplier_read(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    del current_user
    supplier = _get_supplier_or_404(db, supplier_id)
    db.delete(supplier)
    db.commit()


@router.post("/{supplier_id}/reveal-secret", response_model=SupplierSecretRead)
def reveal_supplier_secret(
    supplier_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> SupplierSecretRead:
    supplier = _get_supplier_or_404(db, supplier_id)

    audit_log = AuditLog(
        user_id=current_user.id,
        action="reveal_supplier_secret",
        resource_type="supplier",
        resource_id=supplier.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detail={"supplier_name": supplier.name},
    )
    db.add(audit_log)
    db.commit()

    return SupplierSecretRead(
        id=supplier.id,
        login_account=field_cipher.decrypt(supplier.login_account),
        login_secret=field_cipher.decrypt(supplier.login_secret_encrypted),
    )
