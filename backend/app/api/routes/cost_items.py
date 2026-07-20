import uuid
from datetime import date
from secrets import choice
from string import ascii_uppercase, digits

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.cost_item import CostItem
from app.models.user import User
from app.schemas.cost_item import CostItemCreate, CostItemRead, CostItemUpdate

router = APIRouter(prefix="/api/cost-items", tags=["cost-items"])


def generate_cost_no(today: date | None = None) -> str:
    current_date = today or date.today()
    suffix = "".join(choice(ascii_uppercase + digits) for _ in range(6))
    return f"COST-{current_date:%Y%m%d}-{suffix}"


def _get_cost_item_or_404(db: Session, cost_item_id: uuid.UUID) -> CostItem:
    cost_item = db.get(CostItem, cost_item_id)
    if cost_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost item not found",
        )
    return cost_item


@router.get("", response_model=list[CostItemRead])
def list_cost_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cost_type: str | None = None,
    source_type: str | None = None,
    supplier_id: uuid.UUID | None = None,
    include_all_cost: bool | None = None,
    include_real_cost: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CostItem]:
    del current_user
    stmt = select(CostItem).order_by(CostItem.cost_date.desc(), CostItem.created_at.desc())

    if cost_type:
        stmt = stmt.where(CostItem.cost_type == cost_type)
    if source_type:
        stmt = stmt.where(CostItem.source_type == source_type)
    if supplier_id:
        stmt = stmt.where(CostItem.supplier_id == supplier_id)
    if include_all_cost is not None:
        stmt = stmt.where(CostItem.include_all_cost == include_all_cost)
    if include_real_cost is not None:
        stmt = stmt.where(CostItem.include_real_cost == include_real_cost)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/summary")
def summarize_cost_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, float]:
    del current_user
    all_cost = db.scalar(
        select(func.coalesce(func.sum(CostItem.amount), 0)).where(
            CostItem.include_all_cost.is_(True)
        )
    )
    real_cost = db.scalar(
        select(func.coalesce(func.sum(CostItem.amount), 0)).where(
            CostItem.include_real_cost.is_(True)
        )
    )
    all_cost_float = float(all_cost or 0)
    real_cost_float = float(real_cost or 0)
    return {
        "all_cost": all_cost_float,
        "real_cost": real_cost_float,
        "test_loss": all_cost_float - real_cost_float,
    }


@router.post("", response_model=CostItemRead, status_code=status.HTTP_201_CREATED)
def create_cost_item(
    payload: CostItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> CostItem:
    del current_user
    data = payload.model_dump()
    if not str(data.get("cost_no") or "").strip():
        data["cost_no"] = generate_cost_no()

    cost_item = CostItem(**data)
    db.add(cost_item)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cost number already exists",
        ) from exc

    db.refresh(cost_item)
    return cost_item


@router.get("/{cost_item_id}", response_model=CostItemRead)
def get_cost_item(
    cost_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostItem:
    del current_user
    return _get_cost_item_or_404(db, cost_item_id)


@router.patch("/{cost_item_id}", response_model=CostItemRead)
def update_cost_item(
    cost_item_id: uuid.UUID,
    payload: CostItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> CostItem:
    del current_user
    cost_item = _get_cost_item_or_404(db, cost_item_id)

    if cost_item.source_type == "purchase":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated purchase costs must be updated through the purchase",
        )

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(cost_item, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cost number already exists",
        ) from exc

    db.refresh(cost_item)
    return cost_item


@router.delete("/{cost_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_item(
    cost_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> None:
    del current_user
    cost_item = _get_cost_item_or_404(db, cost_item_id)

    if cost_item.source_type == "purchase":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated purchase costs must be deleted through the purchase",
        )

    db.delete(cost_item)
    db.commit()
