import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha1
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import field_cipher
from app.models.revenue import Revenue
from app.models.sub2api_instance import Sub2APIInstance
from app.services.sub2api_admin_adapter import _extract_items, _headers, _json_or_text, _normalize_base_url

REVENUE_PATH_CANDIDATES = (
    "/api/v1/admin/payment/orders?page=1&page_size=1000",
    "/api/admin/payment/orders?page=1&page_size=1000",
    "/api/v1/admin/orders?page=1&page_size=1000",
    "/api/admin/orders?page=1&page_size=1000",
    "/api/v1/admin/payments?page=1&page_size=1000",
    "/api/admin/payments?page=1&page_size=1000",
    "/api/v1/admin/recharges?page=1&page_size=1000",
    "/api/admin/recharges?page=1&page_size=1000",
)


@dataclass(frozen=True)
class Sub2APIRevenueCandidate:
    remote_order_no: str
    source: str
    customer: str | None
    amount: Decimal
    currency: str
    payment_method: str | None
    revenue_date: date
    received: bool
    raw_payload: dict[str, Any]


@dataclass
class Sub2APIRevenueSyncResult:
    instance_id: uuid.UUID | None
    instance_name: str | None
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    status: str = "success"
    message: str | None = None


def _first_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _date(value: Any) -> date:
    if value is None:
        return datetime.now(UTC).date()
    text = str(value).strip()
    if not text:
        return datetime.now(UTC).date()
    if text.isdigit():
        timestamp = int(text)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).date()
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return datetime.now(UTC).date()


def _received(payload: dict[str, Any]) -> bool:
    status = str(_first_value(payload, ("status", "payment_status", "state")) or "").lower()
    if status in {"paid", "success", "succeeded", "completed", "received", "done"}:
        return True
    if status in {"pending", "unpaid", "failed", "cancelled", "canceled", "voided", "refunded"}:
        return False
    value = _first_value(payload, ("received", "paid", "is_paid"))
    if isinstance(value, bool):
        return value
    return False


def _limit(value: str | None, length: int) -> str | None:
    if value is None:
        return None
    return value[:length]


def normalize_sub2api_revenue(payload: dict[str, Any]) -> Sub2APIRevenueCandidate | None:
    order_no = _first_value(
        payload,
        (
            "out_trade_no",
            "outTradeNo",
            "payment_trade_no",
            "paymentTradeNo",
            "order_no",
            "orderNo",
            "order_id",
            "orderId",
            "trade_no",
            "tradeNo",
            "payment_id",
            "id",
        ),
    )
    amount = _decimal(
        _first_value(
            payload,
            ("pay_amount", "payAmount", "paid_amount", "paidAmount", "amount", "total_amount", "totalAmount", "money"),
        )
    )
    if order_no is None or amount is None:
        return None
    if not _received(payload):
        return None

    customer = _first_value(
        payload,
        ("customer", "customer_name", "user_email", "email", "username", "user_id", "userId"),
    )
    currency = str(_first_value(payload, ("currency", "coin", "unit")) or "USD").upper()
    paid_at = _first_value(
        payload,
        ("paid_at", "paidAt", "payment_time", "paymentTime", "created_at", "createdAt", "created_time"),
    )
    payment_method = _first_value(
        payload,
        ("payment_method", "paymentMethod", "payment_type", "paymentType", "pay_type", "payType", "channel"),
    )
    source = str(_first_value(payload, ("source", "order_type", "orderType", "type", "kind")) or "sub2api_recharge")
    if source in {"balance", "recharge", "payment", "order"}:
        source = f"sub2api_{source}"

    return Sub2APIRevenueCandidate(
        remote_order_no=str(order_no),
        source=source[:50],
        customer=_limit(str(customer), 200) if customer is not None else None,
        amount=amount,
        currency=currency[:20],
        payment_method=_limit(str(payment_method), 100) if payment_method is not None else None,
        revenue_date=_date(paid_at),
        received=True,
        raw_payload=payload,
    )


def fetch_sub2api_revenue_candidates(
    instance: Sub2APIInstance,
    timeout_seconds: int = 20,
) -> list[Sub2APIRevenueCandidate]:
    admin_key = field_cipher.decrypt(instance.admin_key_encrypted) or ""
    if not admin_key:
        raise ValueError("Sub2API 管理员 Key 为空")

    base_url = _normalize_base_url(instance.base_url)
    last_error = ""
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        for path in REVENUE_PATH_CANDIDATES:
            url = urljoin(base_url, path.lstrip("/"))
            response = client.get(url, headers=_headers(admin_key))
            payload = _json_or_text(response)
            if response.status_code == 200:
                return [
                    candidate
                    for item in _extract_items(payload)
                    if (candidate := normalize_sub2api_revenue(item)) is not None
                ]
            last_error = f"{path}: HTTP {response.status_code}"
            if response.status_code in {401, 403}:
                raise ValueError(str(payload.get("message") or payload.get("reason") or "Sub2API 管理员 Key 无效"))
    raise ValueError(last_error or "未发现可用的 Sub2API 收入接口")


def _revenue_no(instance_id: uuid.UUID, remote_order_no: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in remote_order_no)
    value = f"SUB2API-{instance_id}-{cleaned}"
    if len(value) <= 100:
        return value
    digest = sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"SUB2API-{instance_id}-{digest}"


def _related_order_no(instance_id: uuid.UUID, remote_order_no: str) -> str:
    value = f"{instance_id}:{remote_order_no}"
    if len(value) <= 100:
        return value
    digest = sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{instance_id}:{digest}"


def _apply_candidate(revenue: Revenue, candidate: Sub2APIRevenueCandidate) -> None:
    revenue.source = candidate.source
    revenue.customer = candidate.customer
    revenue.amount = candidate.amount
    revenue.currency = candidate.currency
    revenue.payment_method = candidate.payment_method
    revenue.revenue_date = candidate.revenue_date
    revenue.received = candidate.received
    revenue.remark = "Sub2API 自动同步"


def sync_sub2api_revenues_for_instance(
    db: Session,
    instance: Sub2APIInstance,
    timeout_seconds: int = 20,
) -> Sub2APIRevenueSyncResult:
    result = Sub2APIRevenueSyncResult(instance_id=instance.id, instance_name=instance.name)
    try:
        candidates = fetch_sub2api_revenue_candidates(instance, timeout_seconds=timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        result.failed_count = 1
        result.status = "failed"
        result.message = str(exc)
        return result

    related_order_nos = [_related_order_no(instance.id, item.remote_order_no) for item in candidates]
    existing = {
        revenue.related_order_no: revenue
        for revenue in db.scalars(
            select(Revenue).where(Revenue.related_order_no.in_(related_order_nos))
        ).all()
    } if related_order_nos else {}

    for candidate in candidates:
        related_order_no = _related_order_no(instance.id, candidate.remote_order_no)
        revenue = existing.get(related_order_no)
        if revenue is None:
            revenue = Revenue(
                revenue_no=_revenue_no(instance.id, candidate.remote_order_no),
                related_order_no=related_order_no,
                source=candidate.source,
                customer=candidate.customer,
                amount=candidate.amount,
                currency=candidate.currency,
                payment_method=candidate.payment_method,
                revenue_date=candidate.revenue_date,
                received=candidate.received,
                remark="Sub2API 自动同步",
            )
            db.add(revenue)
            result.created_count += 1
        else:
            _apply_candidate(revenue, candidate)
            result.updated_count += 1

    db.commit()
    return result


def sync_sub2api_revenues(
    db: Session,
    timeout_seconds: int = 20,
) -> list[Sub2APIRevenueSyncResult]:
    instances = db.scalars(select(Sub2APIInstance).where(Sub2APIInstance.is_active.is_(True))).all()
    return [
        sync_sub2api_revenues_for_instance(db, instance, timeout_seconds=timeout_seconds)
        for instance in instances
    ]
