import uuid
from datetime import date
from secrets import choice
from string import ascii_uppercase, digits

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.revenue import Revenue
from app.models.user import User
from app.schemas.revenue import RevenueCreate, RevenueRead, RevenueUpdate, Sub2APIRevenueSyncResult
from app.services.sub2api_revenue_sync import sync_sub2api_revenues

router = APIRouter(prefix="/api/revenues", tags=["revenues"])


def generate_revenue_no(today: date | None = None) -> str:
    current = today or date.today()
    suffix = "".join(choice(ascii_uppercase + digits) for _ in range(6))
    return f"REV-{current.strftime('%Y%m%d')}-{suffix}"


def _get_revenue_or_404(db: Session, revenue_id: uuid.UUID) -> Revenue:
    revenue = db.get(Revenue, revenue_id)
    if revenue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue not found",
        )
    return revenue


@router.get("", response_model=list[RevenueRead])
def list_revenues(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    source: str | None = None,
    received: bool | None = None,
    customer: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Revenue]:
    del current_user
    stmt = select(Revenue).order_by(Revenue.revenue_date.desc(), Revenue.created_at.desc())

    if source:
        stmt = stmt.where(Revenue.source == source)
    if received is not None:
        stmt = stmt.where(Revenue.received == received)
    if customer:
        stmt = stmt.where(Revenue.customer.ilike(f"%{customer}%"))

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.post("", response_model=RevenueRead, status_code=status.HTTP_201_CREATED)
def create_revenue(
    payload: RevenueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> Revenue:
    del current_user
    values = payload.model_dump()
    if not values.get("revenue_no"):
        values["revenue_no"] = generate_revenue_no()
    revenue = Revenue(**values)
    db.add(revenue)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revenue number already exists",
        ) from exc

    db.refresh(revenue)
    return revenue


@router.post("/sync-sub2api", response_model=list[Sub2APIRevenueSyncResult])
def sync_revenues_from_sub2api(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> list[Sub2APIRevenueSyncResult]:
    del current_user
    return [
        Sub2APIRevenueSyncResult.model_validate(result.__dict__)
        for result in sync_sub2api_revenues(db)
    ]


@router.get("/{revenue_id}", response_model=RevenueRead)
def get_revenue(
    revenue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Revenue:
    del current_user
    return _get_revenue_or_404(db, revenue_id)


@router.patch("/{revenue_id}", response_model=RevenueRead)
def update_revenue(
    revenue_id: uuid.UUID,
    payload: RevenueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> Revenue:
    del current_user
    revenue = _get_revenue_or_404(db, revenue_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(revenue, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revenue number already exists",
        ) from exc

    db.refresh(revenue)
    return revenue


@router.delete("/{revenue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_revenue(
    revenue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE)),
) -> None:
    del current_user
    revenue = _get_revenue_or_404(db, revenue_id)
    db.delete(revenue)
    db.commit()
