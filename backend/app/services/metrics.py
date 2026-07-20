from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.cost_item import CostItem
from app.models.revenue import Revenue


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def decimal_to_float(value: Decimal | int | float | None) -> float:
    return float(value or 0)


def revenue_sum(db: Session, start: date, end: date) -> float:
    value = db.scalar(
        select(func.coalesce(func.sum(Revenue.amount), 0)).where(
            Revenue.received.is_(True),
            Revenue.revenue_date >= start,
            Revenue.revenue_date < end,
        )
    )
    return decimal_to_float(value)


def cost_sums(db: Session, start: date, end: date) -> tuple[float, float]:
    row = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (CostItem.include_all_cost.is_(True), CostItem.amount),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (CostItem.include_real_cost.is_(True), CostItem.amount),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(CostItem.cost_date >= start, CostItem.cost_date < end)
    ).one()
    return decimal_to_float(row[0]), decimal_to_float(row[1])


def account_status_counts(db: Session) -> tuple[int, int]:
    available = db.scalar(
        select(func.count()).select_from(Account).where(Account.status == "available")
    )
    unavailable = db.scalar(
        select(func.count()).select_from(Account).where(Account.status != "available")
    )
    return int(available or 0), int(unavailable or 0)

