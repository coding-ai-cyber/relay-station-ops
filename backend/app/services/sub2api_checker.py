import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import field_cipher
from app.models.account import Account
from app.models.account_check import AccountCheckBatch, AccountCheckRecord
from app.schemas.account import Sub2APICheckRequest


PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _account_context(account: Account) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "account_no": account.account_no,
        "name": account.name or "",
        "login_account": account.login_account or "",
        "authorized_email": account.authorized_email or "",
        "bind_email": account.bind_email or "",
        "recovery_email": account.recovery_email or "",
        "sub2api_account_id": account.sub2api_account_id or "",
        "sub2api_key": field_cipher.decrypt(account.sub2api_key_encrypted) or "",
        "account_type": account.account_type,
        "plan_type": account.plan_type or "",
    }


def _render(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return PLACEHOLDER_RE.sub(lambda match: str(context.get(match.group(1), "")), value)
    if isinstance(value, dict):
        return {key: _render(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render(item, context) for item in value]
    return value


def _extract_error_code(payload: Any, status_code: int | None) -> str | None:
    if isinstance(payload, dict):
        for key in ("error_code", "code", "status", "type"):
            value = payload.get(key)
            if value is not None:
                return str(value)
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("code", "type", "message"):
                value = error.get(key)
                if value is not None:
                    return str(value)
        if isinstance(error, str):
            return error[:100]
    return str(status_code) if status_code is not None and status_code >= 400 else None


def _extract_message(payload: Any, fallback: str | None = None) -> str | None:
    if isinstance(payload, dict):
        for key in ("message", "msg", "detail"):
            value = payload.get(key)
            if value is not None:
                return str(value)
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("message", "detail", "code"):
                value = error.get(key)
                if value is not None:
                    return str(value)
        if isinstance(error, str):
            return error
    return fallback


def _status_from_http(status_code: int | None) -> tuple[bool, str]:
    if status_code is not None and 200 <= status_code < 300:
        return True, "available"
    if status_code == 401:
        return False, "api_401"
    if status_code == 403:
        return False, "api_403"
    if status_code == 429:
        return False, "api_429"
    if status_code is None:
        return False, "check_failed"
    return False, "unavailable"


def _survival_seconds(account: Account, now: datetime) -> int | None:
    start = account.first_seen_alive_at or account.available_started_at or account.created_at
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return max(0, int((now - start).total_seconds()))


def _select_accounts(db: Session, payload: Sub2APICheckRequest) -> list[Account]:
    stmt = select(Account).order_by(Account.created_at.asc())
    if payload.account_ids:
        stmt = stmt.where(Account.id.in_(payload.account_ids))
    if payload.supplier_id:
        stmt = stmt.where(Account.supplier_id == payload.supplier_id)
    if payload.purchase_id:
        stmt = stmt.where(Account.purchase_id == payload.purchase_id)
    if payload.account_type:
        stmt = stmt.where(Account.account_type == payload.account_type)
    if payload.import_batch_no:
        stmt = stmt.where(Account.import_batch_no == payload.import_batch_no)
    if payload.include_only_operation:
        stmt = stmt.where(Account.participate_operation.is_(True))
    return db.scalars(stmt).all()


def run_sub2api_check(
    db: Session,
    payload: Sub2APICheckRequest,
    checked_by: uuid.UUID | None,
) -> AccountCheckBatch:
    now = datetime.now(UTC)
    accounts = _select_accounts(db, payload)
    batch = AccountCheckBatch(
        batch_no=f"CHK-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        name=f"Sub2API账号检测 {now.strftime('%Y-%m-%d %H:%M:%S')}",
        source="sub2api",
        endpoint_url=str(payload.endpoint_url),
        method=payload.method,
        checked_by=checked_by,
        total_count=len(accounts),
        started_at=now,
        request_config=payload.model_dump(mode="json", exclude={"auth_header_value"}),
        remark=payload.remark,
    )
    db.add(batch)
    db.flush()

    headers: dict[str, str] = {}
    if payload.auth_header_name and payload.auth_header_value:
        headers[payload.auth_header_name] = payload.auth_header_value

    with httpx.Client(timeout=payload.timeout_seconds) as client:
        for account in accounts:
            context = _account_context(account)
            url = _render(str(payload.endpoint_url), context)
            request_body = _render(payload.request_body or {}, context)
            started = time.perf_counter()
            status_code: int | None = None
            raw_response: dict[str, Any] | None = None
            error_message: str | None = None

            try:
                if payload.method == "POST":
                    response = client.post(url, headers=headers, json=request_body)
                else:
                    response = client.get(url, headers=headers)
                status_code = response.status_code
                try:
                    parsed: Any = response.json()
                    raw_response = parsed if isinstance(parsed, dict) else {"data": parsed}
                except ValueError:
                    raw_response = {"text": response.text[:2000]}
            except Exception as exc:  # noqa: BLE001
                raw_response = {"exception": exc.__class__.__name__}
                error_message = str(exc)

            response_ms = int((time.perf_counter() - started) * 1000)
            is_alive, sub2api_status = _status_from_http(status_code)
            error_code = _extract_error_code(raw_response, status_code)
            error_message = _extract_message(raw_response, error_message)

            if is_alive:
                if account.first_seen_alive_at is None:
                    account.first_seen_alive_at = now
                if account.available_started_at is None:
                    account.available_started_at = now
                account.last_seen_alive_at = now
                account.status = "available"
                batch.alive_count += 1
            else:
                if account.first_abnormal_at is None:
                    account.first_abnormal_at = now
                account.status = sub2api_status
                batch.abnormal_count += 1
                if status_code == 401:
                    batch.status_401_count += 1
                elif status_code == 403:
                    batch.status_403_count += 1
                elif status_code == 429:
                    batch.status_429_count += 1

            account.last_checked_at = now
            account.last_sub2api_status_code = status_code
            account.last_sub2api_error_code = error_code
            account.last_sub2api_message = error_message
            account.survival_seconds = _survival_seconds(account, now)
            account.available_days = (
                account.survival_seconds // 86400 if account.survival_seconds is not None else None
            )

            db.add(
                AccountCheckRecord(
                    batch_id=batch.id,
                    account_id=account.id,
                    checked_at=now,
                    http_status=status_code,
                    sub2api_status=sub2api_status,
                    is_alive=is_alive,
                    error_code=error_code,
                    error_message=error_message,
                    response_ms=response_ms,
                    survived_seconds=account.survival_seconds,
                    raw_response=raw_response,
                )
            )

    batch.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(batch)
    return batch
