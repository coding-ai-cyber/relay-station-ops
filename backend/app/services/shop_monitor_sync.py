from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.shop_monitor import ShopMonitor, ShopProduct
from app.schemas.shop_monitor import ShopMonitorSyncResult
from app.services.link_shop_monitor import LinkShopClient


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_shop_monitor_due_for_auto_sync(
    monitor: ShopMonitor,
    *,
    now: datetime,
    success_interval_seconds: int,
    failure_cooldown_seconds: int,
) -> bool:
    if not monitor.enabled:
        return False
    if monitor.last_synced_at is None:
        return True

    interval_seconds = (
        failure_cooldown_seconds
        if monitor.last_sync_status == "failed"
        else success_interval_seconds
    )
    return _as_utc(monitor.last_synced_at) <= _as_utc(now) - timedelta(seconds=interval_seconds)


def build_due_shop_monitor_statement(
    *,
    now: datetime,
    success_interval_seconds: int,
    failure_cooldown_seconds: int,
    max_monitors: int | None = None,
):
    now = _as_utc(now)
    success_cutoff = now - timedelta(seconds=success_interval_seconds)
    failure_cutoff = now - timedelta(seconds=failure_cooldown_seconds)
    statement = (
        select(ShopMonitor)
        .where(
            ShopMonitor.enabled.is_(True),
            or_(
                ShopMonitor.last_synced_at.is_(None),
                and_(
                    ShopMonitor.last_sync_status == "failed",
                    ShopMonitor.last_synced_at <= failure_cutoff,
                ),
                and_(
                    ShopMonitor.last_sync_status != "failed",
                    ShopMonitor.last_synced_at <= success_cutoff,
                ),
            ),
        )
        .order_by(ShopMonitor.last_synced_at.asc().nullsfirst(), ShopMonitor.created_at.asc())
        .with_for_update(skip_locked=True)
    )
    if max_monitors is not None:
        statement = statement.limit(max_monitors)
    return statement


def sync_monitor(db: Session, monitor: ShopMonitor) -> ShopMonitorSyncResult:
    client = LinkShopClient(platform=monitor.platform)
    try:
        shop_info, products = client.fetch_products(monitor.shop_token)
        monitor.name = shop_info.get("nickname") or monitor.name
        monitor.raw_shop_payload = shop_info
        monitor.last_synced_at = datetime.now(UTC)
        monitor.last_sync_status = "success"
        monitor.last_sync_message = None

        existing = {
            product.external_product_id: product
            for product in db.scalars(
                select(ShopProduct).where(ShopProduct.monitor_id == monitor.id)
            )
        }
        seen_ids: set[str] = set()
        for payload in products:
            external_id = payload["external_product_id"]
            seen_ids.add(external_id)
            product = existing.get(external_id)
            if product is None:
                product = ShopProduct(monitor_id=monitor.id, external_product_id=external_id)
                db.add(product)
            product.goods_type = payload["goods_type"]
            product.category_id = payload["category_id"]
            product.category_name = payload["category_name"]
            product.standard_category_key = payload["standard_category_key"]
            product.standard_category_name = payload["standard_category_name"]
            product.category_duplicate_status = payload["category_duplicate_status"]
            product.name = payload["name"]
            product.price = Decimal(payload["price"])
            product.market_price = (
                Decimal(payload["market_price"]) if payload["market_price"] is not None else None
            )
            product.stock_count = payload["stock_count"]
            product.is_out_of_stock = payload["is_out_of_stock"]
            product.raw_payload = payload["raw_payload"]

        for external_id, product in existing.items():
            if external_id not in seen_ids:
                product.stock_count = 0
                product.is_out_of_stock = True

        product_count = len(products)
        out_of_stock_count = sum(1 for product in products if product["is_out_of_stock"])
        db.commit()
        db.refresh(monitor)
        return ShopMonitorSyncResult(
            monitor_id=monitor.id,
            product_count=product_count,
            out_of_stock_count=out_of_stock_count,
            status="success",
        )
    except Exception as exc:
        monitor.last_synced_at = datetime.now(UTC)
        monitor.last_sync_status = "failed"
        monitor.last_sync_message = str(exc)
        db.commit()
        return ShopMonitorSyncResult(
            monitor_id=monitor.id,
            product_count=0,
            out_of_stock_count=0,
            status="failed",
            message=str(exc),
        )


def sync_enabled_shop_monitors(
    db: Session,
    *,
    now: datetime | None = None,
    success_interval_seconds: int | None = None,
    failure_cooldown_seconds: int | None = None,
    max_monitors: int | None = None,
) -> list[ShopMonitorSyncResult]:
    statement = build_due_shop_monitor_statement(
        now=now or datetime.now(UTC),
        success_interval_seconds=(
            success_interval_seconds
            if success_interval_seconds is not None
            else settings.shop_monitor_success_interval_seconds
        ),
        failure_cooldown_seconds=(
            failure_cooldown_seconds
            if failure_cooldown_seconds is not None
            else settings.shop_monitor_failure_cooldown_seconds
        ),
        max_monitors=max_monitors
        if max_monitors is not None
        else settings.shop_monitor_max_per_batch,
    )
    monitors = db.scalars(statement).all()
    if max_monitors is not None:
        monitors = monitors[:max_monitors]
    return [sync_monitor(db, monitor) for monitor in monitors]
