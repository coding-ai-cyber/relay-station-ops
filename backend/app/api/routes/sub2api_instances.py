import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import field_cipher
from app.db.session import get_db
from app.models.sub2api_instance import Sub2APIInstance
from app.models.user import User
from app.models.account import Account
from app.models.account_check import AccountCheckBatch
from app.schemas.sub2api_instance import (
    Sub2APIInstanceCreate,
    Sub2APIInstanceRead,
    Sub2APIInstanceUpdate,
    Sub2APIProbeResult,
)
from app.schemas.sub2api_import import Sub2APIGroupRead, Sub2APIProxyRead
from app.services.sub2api_admin_adapter import probe_sub2api_instance
from app.services.sub2api_importer import (
    Sub2APIImportError,
    fetch_sub2api_groups,
    fetch_sub2api_proxies,
)

router = APIRouter(prefix="/api/sub2api-instances", tags=["sub2api-instances"])


def _to_read(instance: Sub2APIInstance) -> Sub2APIInstanceRead:
    return Sub2APIInstanceRead.model_validate(
        {
            **instance.__dict__,
            "has_admin_key": bool(instance.admin_key_encrypted),
        }
    )


def _get_or_404(db: Session, instance_id: uuid.UUID) -> Sub2APIInstance:
    instance = db.get(Sub2APIInstance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub2API instance not found")
    return instance


@router.get("", response_model=list[Sub2APIInstanceRead])
def list_sub2api_instances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Sub2APIInstanceRead]:
    del current_user
    stmt = select(Sub2APIInstance).order_by(Sub2APIInstance.created_at.desc())
    return [_to_read(item) for item in db.scalars(stmt).all()]


@router.post("", response_model=Sub2APIInstanceRead, status_code=status.HTTP_201_CREATED)
def create_sub2api_instance(
    payload: Sub2APIInstanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Sub2APIInstanceRead:
    del current_user
    instance = Sub2APIInstance(
        name=payload.name,
        base_url=str(payload.base_url).rstrip("/"),
        admin_key_encrypted=field_cipher.encrypt(payload.admin_key),
        is_active=payload.is_active,
        adapter=payload.adapter,
        remark=payload.remark,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return _to_read(instance)


@router.patch("/{instance_id}", response_model=Sub2APIInstanceRead)
def update_sub2api_instance(
    instance_id: uuid.UUID,
    payload: Sub2APIInstanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> Sub2APIInstanceRead:
    del current_user
    instance = _get_or_404(db, instance_id)
    data = payload.model_dump(exclude_unset=True)
    if "admin_key" in data:
        instance.admin_key_encrypted = field_cipher.encrypt(data.pop("admin_key"))
    if "base_url" in data and data["base_url"] is not None:
        data["base_url"] = str(data["base_url"]).rstrip("/")
    for field_name, value in data.items():
        setattr(instance, field_name, value)
    db.commit()
    db.refresh(instance)
    return _to_read(instance)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub2api_instance(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    del current_user
    instance = _get_or_404(db, instance_id)

    for account in db.scalars(
        select(Account).where(Account.sub2api_instance_id == instance.id)
    ).all():
        account.sub2api_instance_id = None
    for batch in db.scalars(
        select(AccountCheckBatch).where(AccountCheckBatch.sub2api_instance_id == instance.id)
    ).all():
        batch.sub2api_instance_id = None

    db.delete(instance)
    db.commit()


@router.post("/{instance_id}/probe", response_model=Sub2APIProbeResult)
def probe_instance(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)),
) -> Sub2APIProbeResult:
    del current_user
    instance = _get_or_404(db, instance_id)
    probe = probe_sub2api_instance(instance)
    instance.last_probe_status = probe.status
    instance.last_probe_message = probe.message
    if probe.accounts_path:
        instance.detected_accounts_path = probe.accounts_path
    db.commit()
    return Sub2APIProbeResult(
        ok=probe.ok,
        status=probe.status,
        message=probe.message,
        accounts_path=probe.accounts_path,
        version=probe.version,
        sample_count=probe.sample_count,
    )


@router.get("/{instance_id}/groups", response_model=list[Sub2APIGroupRead])
def list_instance_groups(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> list[Sub2APIGroupRead]:
    del current_user
    instance = _get_or_404(db, instance_id)
    try:
        groups = fetch_sub2api_groups(instance)
    except Sub2APIImportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [
        Sub2APIGroupRead(
            id=int(group["id"]),
            name=str(group.get("name") or group["id"]),
            platform=str(group.get("platform") or ""),
            status=str(group["status"]) if group.get("status") is not None else None,
            is_exclusive=bool(group["is_exclusive"]) if group.get("is_exclusive") is not None else None,
        )
        for group in groups
        if group.get("id") is not None
    ]


@router.get("/{instance_id}/proxies", response_model=list[Sub2APIProxyRead])
def list_instance_proxies(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> list[Sub2APIProxyRead]:
    del current_user
    instance = _get_or_404(db, instance_id)
    try:
        proxies = fetch_sub2api_proxies(instance)
    except Sub2APIImportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [
        Sub2APIProxyRead(
            id=int(proxy["id"]),
            name=str(proxy.get("name") or proxy["id"]),
            protocol=str(proxy["protocol"]) if proxy.get("protocol") is not None else None,
            host=str(proxy["host"]) if proxy.get("host") is not None else None,
            port=int(proxy["port"]) if proxy.get("port") is not None else None,
            username=str(proxy["username"]) if proxy.get("username") is not None else None,
            status=str(proxy["status"]) if proxy.get("status") is not None else None,
            latency_ms=int(proxy["latency_ms"]) if proxy.get("latency_ms") is not None else None,
            latency_status=str(proxy["latency_status"]) if proxy.get("latency_status") is not None else None,
            account_count=int(proxy["account_count"]) if proxy.get("account_count") is not None else None,
        )
        for proxy in proxies
        if proxy.get("id") is not None
    ]
