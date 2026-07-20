import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.shop_monitor import ShopMonitor
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.shop_monitor import (
    ShopMonitorCreate,
    ShopMonitorImportResult,
    ShopMonitorRead,
    ShopMonitorSyncResult,
)
from app.services.link_shop_monitor import parse_shop_reference
from app.services.shop_monitor_sync import sync_enabled_shop_monitors, sync_monitor

router = APIRouter(prefix="/api/shop-monitors", tags=["shop-monitors"])


def _get_monitor_or_404(db: Session, monitor_id: uuid.UUID) -> ShopMonitor:
    monitor = db.scalar(
        select(ShopMonitor)
        .options(selectinload(ShopMonitor.products))
        .where(ShopMonitor.id == monitor_id)
    )
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop monitor not found",
        )
    return monitor


@router.get("", response_model=list[ShopMonitorRead])
def list_shop_monitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShopMonitor]:
    del current_user
    return list(
        db.scalars(
            select(ShopMonitor)
            .options(selectinload(ShopMonitor.products))
            .order_by(ShopMonitor.updated_at.desc())
        ).all()
    )


def collect_supplier_shop_monitor_imports(
    suppliers: list[Supplier],
    existing_refs: set[tuple[str, str]],
) -> tuple[list[dict], int]:
    payloads: list[dict] = []
    skipped_count = 0
    for supplier in suppliers:
        if supplier.type != "account" or not supplier.monitor_shop or not supplier.login_url:
            skipped_count += 1
            continue
        try:
            platform, token = parse_shop_reference(supplier.login_url)
        except ValueError:
            skipped_count += 1
            continue
        ref = (platform.platform, token)
        if ref in existing_refs:
            skipped_count += 1
            continue
        payloads.append(
            {
                "supplier_id": supplier.id,
                "name": supplier.name,
                "shop_url": supplier.login_url,
                "shop_token": token,
                "platform": platform.platform,
                "enabled": True,
            }
        )
        existing_refs.add(ref)
    return payloads, skipped_count


@router.post("", response_model=ShopMonitorRead, status_code=status.HTTP_201_CREATED)
def create_shop_monitor(
    payload: ShopMonitorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> ShopMonitor:
    del current_user
    try:
        platform, token = parse_shop_reference(payload.shop_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    monitor = ShopMonitor(
        supplier_id=payload.supplier_id,
        name=payload.name or token,
        shop_url=payload.shop_url,
        shop_token=token,
        platform=platform.platform,
        enabled=payload.enabled,
    )
    db.add(monitor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shop monitor already exists",
        ) from exc
    db.refresh(monitor)
    return monitor


@router.post("/import-suppliers", response_model=ShopMonitorImportResult)
def import_supplier_shop_monitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> ShopMonitorImportResult:
    del current_user
    existing_refs = {
        (platform, token)
        for platform, token in db.execute(
            select(ShopMonitor.platform, ShopMonitor.shop_token)
        ).all()
    }
    suppliers = db.scalars(
        select(Supplier).where(
            Supplier.type == "account",
            Supplier.monitor_shop.is_(True),
            Supplier.login_url.is_not(None),
        )
    ).all()
    payloads, skipped_count = collect_supplier_shop_monitor_imports(suppliers, existing_refs)
    for payload in payloads:
        db.add(ShopMonitor(**payload))
    db.commit()
    return ShopMonitorImportResult(created_count=len(payloads), skipped_count=skipped_count)


@router.post("/sync-all", response_model=list[ShopMonitorSyncResult])
def sync_all_shop_monitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> list[ShopMonitorSyncResult]:
    del current_user
    return sync_enabled_shop_monitors(db)


@router.post("/{monitor_id}/sync", response_model=ShopMonitorSyncResult)
def sync_shop_monitor(
    monitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> ShopMonitorSyncResult:
    del current_user
    monitor = _get_monitor_or_404(db, monitor_id)
    return sync_monitor(db, monitor)
