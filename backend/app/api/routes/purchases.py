import uuid
from datetime import date, datetime
from secrets import choice
from string import ascii_uppercase, digits

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.account import Account
from app.models.cost_item import CostItem
from app.models.proxy_pool import ProxyPool
from app.models.purchase import Purchase
from app.models.server import Server
from app.models.user import User
from app.schemas.purchase import (
    PurchaseAccountJsonBindRequest,
    PurchaseAccountJsonBindResult,
    PurchaseAssetGenerationRequest,
    PurchaseAssetGenerationResult,
    PurchaseCreate,
    PurchaseRead,
    PurchaseUpdate,
)
from app.services.purchase_account_json import bind_purchase_account_json
from app.services.purchase_costs import make_purchase_cost_item, sync_purchase_cost_item

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def generate_purchase_no(today: date | None = None) -> str:
    current_date = today or date.today()
    suffix = "".join(choice(ascii_uppercase + digits) for _ in range(6))
    return f"PO-{current_date:%Y%m%d}-{suffix}"


def _get_purchase_or_404(db: Session, purchase_id: uuid.UUID) -> Purchase:
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found",
        )
    return purchase


def _get_generated_cost_item(db: Session, purchase: Purchase) -> CostItem | None:
    return db.scalar(
        select(CostItem).where(
            CostItem.source_type == "purchase",
            CostItem.source_id == purchase.id,
        )
    )


def _purchase_account_quantity(purchase: Purchase) -> int:
    quantity = purchase.quantity
    if quantity is None or quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("Account purchase quantity must be a positive integer")
    return int(quantity)


def _make_account_assets_from_purchase(
    purchase: Purchase,
    expired_at: datetime | None = None,
) -> list[Account]:
    quantity = _purchase_account_quantity(purchase)
    unit_cost = purchase.total_price / quantity
    return [
        Account(
            account_no=f"{purchase.purchase_no}-A001",
            name=purchase.product_name,
            supplier_id=purchase.supplier_id,
            purchase_id=purchase.id,
            account_type=purchase.product_type or "other",
            plan_type=None,
            status="pending_test",
            expired_at=expired_at,
            participate_operation=False,
            include_real_cost=purchase.include_real_cost,
            cost_unit_price=unit_cost,
            raw_payload={
                "source": "purchase_asset_generation",
                "purchase_no": purchase.purchase_no,
                "purchase_quantity": str(purchase.quantity),
                "asset_index": 1,
                "note": "Account asset generated from one purchase record",
            },
            remark=f"Generated from purchase {purchase.purchase_no}",
        )
    ]


@router.get("", response_model=list[PurchaseRead])
def list_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    purchase_type: str | None = Query(default=None, alias="type"),
    cost_status: str | None = None,
    supplier_id: uuid.UUID | None = None,
    include_real_cost: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Purchase]:
    del current_user
    stmt = select(Purchase).order_by(Purchase.purchased_at.desc(), Purchase.created_at.desc())

    if purchase_type:
        stmt = stmt.where(Purchase.purchase_type == purchase_type)
    if cost_status:
        stmt = stmt.where(Purchase.cost_status == cost_status)
    if supplier_id:
        stmt = stmt.where(Purchase.supplier_id == supplier_id)
    if include_real_cost is not None:
        stmt = stmt.where(Purchase.include_real_cost == include_real_cost)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.post("", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> Purchase:
    data = payload.model_dump()
    if not str(data.get("purchase_no") or "").strip():
        data["purchase_no"] = generate_purchase_no()
    if data.get("purchaser_id") is None:
        data["purchaser_id"] = current_user.id

    purchase = Purchase(**data)
    db.add(purchase)
    db.flush()
    db.add(make_purchase_cost_item(purchase))

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Purchase number or generated cost number already exists",
        ) from exc

    db.refresh(purchase)
    return purchase


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(
    purchase_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Purchase:
    del current_user
    return _get_purchase_or_404(db, purchase_id)


@router.patch("/{purchase_id}", response_model=PurchaseRead)
def update_purchase(
    purchase_id: uuid.UUID,
    payload: PurchaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> Purchase:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)
    data = payload.model_dump(exclude_unset=True)

    for field_name, value in data.items():
        setattr(purchase, field_name, value)

    cost_item = _get_generated_cost_item(db, purchase)
    if cost_item is None:
        db.add(make_purchase_cost_item(purchase))
    else:
        sync_purchase_cost_item(cost_item, purchase)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Purchase number or generated cost number already exists",
        ) from exc

    db.refresh(purchase)
    return purchase


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(
    purchase_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> None:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)
    generated_cost = _get_generated_cost_item(db, purchase)
    if generated_cost is not None:
        db.delete(generated_cost)

    for account in purchase.accounts:
        account.purchase_id = None
    for server in purchase.servers:
        server.purchase_id = None
    for proxy_pool in purchase.proxy_pools:
        proxy_pool.purchase_id = None
    for batch in purchase.evaluation_batches:
        batch.purchase_id = None

    db.delete(purchase)
    db.commit()


@router.post("/{purchase_id}/update-cost-flags", response_model=PurchaseRead)
def update_purchase_cost_flags(
    purchase_id: uuid.UUID,
    include_all_cost: bool | None = None,
    include_real_cost: bool | None = None,
    cost_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> Purchase:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)

    if include_all_cost is not None:
        purchase.include_all_cost = include_all_cost
    if include_real_cost is not None:
        purchase.include_real_cost = include_real_cost
    if cost_status is not None:
        purchase.cost_status = cost_status

    cost_item = _get_generated_cost_item(db, purchase)
    if cost_item is None:
        db.add(make_purchase_cost_item(purchase))
    else:
        sync_purchase_cost_item(cost_item, purchase)

    db.commit()
    db.refresh(purchase)
    return purchase


@router.post("/{purchase_id}/create-assets", response_model=PurchaseAssetGenerationResult)
def create_assets_from_purchase(
    purchase_id: uuid.UUID,
    payload: PurchaseAssetGenerationRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> PurchaseAssetGenerationResult:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)
    expired_at = payload.expired_at if payload else None
    result = PurchaseAssetGenerationResult(
        purchase_id=purchase.id,
        purchase_no=purchase.purchase_no,
        purchase_type=purchase.purchase_type,
    )

    if purchase.purchase_type == "account":
        existing = db.scalar(select(Account).where(Account.purchase_id == purchase.id))
        if existing:
            result.skipped_reason = "Assets already exist for this purchase"
            return result

        try:
            accounts = _make_account_assets_from_purchase(purchase, expired_at=expired_at)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        db.add_all(accounts)
        result.created_accounts = len(accounts)
    elif purchase.purchase_type == "server":
        existing = db.scalar(select(Server).where(Server.purchase_id == purchase.id))
        if existing:
            result.skipped_reason = "Assets already exist for this purchase"
            return result

        server = Server(
            name=purchase.product_name,
            supplier_id=purchase.supplier_id,
            purchase_id=purchase.id,
            monthly_cost=purchase.total_price,
            expired_at=expired_at,
            usage="other",
            status="running",
            include_real_cost=purchase.include_real_cost,
            remark=f"Generated from purchase {purchase.purchase_no}",
        )
        db.add(server)
        result.created_servers = 1
    elif purchase.purchase_type == "proxy":
        existing = db.scalar(select(ProxyPool).where(ProxyPool.purchase_id == purchase.id))
        if existing:
            result.skipped_reason = "Assets already exist for this purchase"
            return result

        proxy_pool = ProxyPool(
            supplier_id=purchase.supplier_id,
            purchase_id=purchase.id,
            proxy_type=purchase.product_type or "other",
            quantity_or_traffic=str(purchase.quantity),
            unit_price=purchase.unit_price,
            total_price=purchase.total_price,
            expired_at=expired_at,
            status="active",
            continue_purchase=True,
            include_real_cost=purchase.include_real_cost,
            remark=f"Generated from purchase {purchase.purchase_no}",
        )
        db.add(proxy_pool)
        result.created_proxy_pools = 1
    else:
        result.skipped_reason = "This purchase type does not support asset generation"
        return result

    db.commit()
    return result


@router.post("/{purchase_id}/accounts/bind-json", response_model=PurchaseAccountJsonBindResult)
def bind_purchase_accounts_json(
    purchase_id: uuid.UUID,
    payload: PurchaseAccountJsonBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> PurchaseAccountJsonBindResult:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)
    if purchase.purchase_type != "account":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only account purchases can bind account JSON",
        )
    try:
        return bind_purchase_account_json(
            db=db,
            purchase=purchase,
            payload=payload.payload,
            file_id=payload.file_id,
            overwrite_existing=payload.overwrite_existing,
            account_type=payload.account_type,
            plan_type=payload.plan_type,
            remark=payload.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
