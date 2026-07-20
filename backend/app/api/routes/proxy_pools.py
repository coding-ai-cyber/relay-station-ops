import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.proxy_pool import ProxyPool
from app.models.user import User
from app.schemas.proxy_pool import ProxyPoolCreate, ProxyPoolRead, ProxyPoolUpdate

router = APIRouter(prefix="/api/proxy-pools", tags=["proxy-pools"])


def _get_proxy_pool_or_404(db: Session, proxy_pool_id: uuid.UUID) -> ProxyPool:
    proxy_pool = db.get(ProxyPool, proxy_pool_id)
    if proxy_pool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy pool not found",
        )
    return proxy_pool


@router.get("", response_model=list[ProxyPoolRead])
def list_proxy_pools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    proxy_type: str | None = Query(default=None, alias="type"),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = None,
    purchase_id: uuid.UUID | None = None,
    suitable_for_login: bool | None = None,
    suitable_for_api: bool | None = None,
    continue_purchase: bool | None = None,
    include_real_cost: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ProxyPool]:
    del current_user
    stmt = select(ProxyPool).order_by(ProxyPool.created_at.desc())

    if proxy_type:
        stmt = stmt.where(ProxyPool.proxy_type == proxy_type)
    if status_filter:
        stmt = stmt.where(ProxyPool.status == status_filter)
    if supplier_id:
        stmt = stmt.where(ProxyPool.supplier_id == supplier_id)
    if purchase_id:
        stmt = stmt.where(ProxyPool.purchase_id == purchase_id)
    if suitable_for_login is not None:
        stmt = stmt.where(ProxyPool.suitable_for_login == suitable_for_login)
    if suitable_for_api is not None:
        stmt = stmt.where(ProxyPool.suitable_for_api == suitable_for_api)
    if continue_purchase is not None:
        stmt = stmt.where(ProxyPool.continue_purchase == continue_purchase)
    if include_real_cost is not None:
        stmt = stmt.where(ProxyPool.include_real_cost == include_real_cost)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.post("", response_model=ProxyPoolRead, status_code=status.HTTP_201_CREATED)
def create_proxy_pool(
    payload: ProxyPoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> ProxyPool:
    del current_user
    proxy_pool = ProxyPool(**payload.model_dump())
    db.add(proxy_pool)
    db.commit()
    db.refresh(proxy_pool)
    return proxy_pool


@router.get("/{proxy_pool_id}", response_model=ProxyPoolRead)
def get_proxy_pool(
    proxy_pool_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProxyPool:
    del current_user
    return _get_proxy_pool_or_404(db, proxy_pool_id)


@router.patch("/{proxy_pool_id}", response_model=ProxyPoolRead)
def update_proxy_pool(
    proxy_pool_id: uuid.UUID,
    payload: ProxyPoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> ProxyPool:
    del current_user
    proxy_pool = _get_proxy_pool_or_404(db, proxy_pool_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(proxy_pool, field_name, value)

    db.commit()
    db.refresh(proxy_pool)
    return proxy_pool


@router.delete("/{proxy_pool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy_pool(
    proxy_pool_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> None:
    del current_user
    proxy_pool = _get_proxy_pool_or_404(db, proxy_pool_id)
    db.delete(proxy_pool)
    db.commit()
