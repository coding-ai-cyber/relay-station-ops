from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.accounts import to_account_read
from app.db.session import get_db
from app.models.account import Account
from app.models.proxy_pool import ProxyPool
from app.models.purchase import Purchase
from app.models.server import Server
from app.models.user import User
from app.schemas.dashboard import DashboardOverview, ExpiringAssetRow
from app.schemas.account import AccountRead
from app.schemas.purchase import PurchaseRead
from app.services.metrics import account_status_counts, cost_sums, month_bounds, revenue_sum

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def resolve_dashboard_period(
    year: int,
    month: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[date, date]:
    if start_date and end_date:
        return start_date, end_date + timedelta(days=1)
    return month_bounds(year, month)


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    start_date: date | None = None,
    end_date: date | None = None,
) -> DashboardOverview:
    del current_user
    start, end = resolve_dashboard_period(year, month, start_date, end_date)
    revenue = revenue_sum(db, start, end)
    all_cost, real_cost = cost_sums(db, start, end)
    available_accounts, unavailable_accounts = account_status_counts(db)
    return DashboardOverview(
        revenue=revenue,
        all_cost=all_cost,
        real_cost=real_cost,
        profit=revenue - all_cost,
        real_profit=revenue - real_cost,
        test_loss=all_cost - real_cost,
        available_accounts=available_accounts,
        unavailable_accounts=unavailable_accounts,
    )


@router.get("/recent-purchases", response_model=list[PurchaseRead])
def recent_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[Purchase]:
    del current_user
    stmt = (
        select(Purchase)
        .order_by(Purchase.purchased_at.desc(), Purchase.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


@router.get("/abnormal-accounts", response_model=list[AccountRead])
def abnormal_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[AccountRead]:
    del current_user
    stmt = (
        select(Account)
        .where(Account.status.in_(["unavailable", "risk_control", "banned", "abandoned"]))
        .order_by(Account.updated_at.desc())
        .limit(limit)
    )
    return [to_account_read(account) for account in db.scalars(stmt).all()]


@router.get("/expiring-assets", response_model=list[ExpiringAssetRow])
def expiring_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ExpiringAssetRow]:
    del current_user
    now = datetime.now(UTC)
    end = now + timedelta(days=days)
    rows: list[ExpiringAssetRow] = []

    accounts = db.scalars(
        select(Account)
        .where(Account.expired_at.is_not(None), Account.expired_at >= now, Account.expired_at <= end)
        .order_by(Account.expired_at.asc())
        .limit(limit)
    ).all()
    rows.extend(
        ExpiringAssetRow(
            asset_id=str(account.id),
            asset_type="account",
            name=account.account_no,
            status=account.status,
            expired_at=account.expired_at.isoformat(),
            days_left=max((account.expired_at.date() - now.date()).days, 0),
            include_real_cost=account.include_real_cost,
        )
        for account in accounts
        if account.expired_at is not None
    )

    servers = db.scalars(
        select(Server)
        .where(Server.expired_at.is_not(None), Server.expired_at >= now, Server.expired_at <= end)
        .order_by(Server.expired_at.asc())
        .limit(limit)
    ).all()
    rows.extend(
        ExpiringAssetRow(
            asset_id=str(server.id),
            asset_type="server",
            name=server.name,
            status=server.status,
            expired_at=server.expired_at.isoformat(),
            days_left=max((server.expired_at.date() - now.date()).days, 0),
            include_real_cost=server.include_real_cost,
        )
        for server in servers
        if server.expired_at is not None
    )

    proxy_pools = db.scalars(
        select(ProxyPool)
        .where(ProxyPool.expired_at.is_not(None), ProxyPool.expired_at >= now, ProxyPool.expired_at <= end)
        .order_by(ProxyPool.expired_at.asc())
        .limit(limit)
    ).all()
    rows.extend(
        ExpiringAssetRow(
            asset_id=str(proxy_pool.id),
            asset_type="proxy_pool",
            name=f"{proxy_pool.proxy_type} / {proxy_pool.region or '-'}",
            status=proxy_pool.status,
            expired_at=proxy_pool.expired_at.isoformat(),
            days_left=max((proxy_pool.expired_at.date() - now.date()).days, 0),
            include_real_cost=proxy_pool.include_real_cost,
        )
        for proxy_pool in proxy_pools
        if proxy_pool.expired_at is not None
    )

    return sorted(rows, key=lambda row: row.expired_at)[:limit]
