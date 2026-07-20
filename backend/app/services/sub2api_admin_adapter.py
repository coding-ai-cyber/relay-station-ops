import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import field_cipher
from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.account_check import AccountCheckBatch, AccountCheckRecord
from app.models.sub2api_instance import Sub2APIInstance
from app.services.account_credentials import redact_raw_payload
from app.services.sub2api_importer import _instance_remote_ids


ACCOUNTS_PATH_CANDIDATES = (
    "/api/v1/admin/accounts?page=1&page_size=1000&lite=true",
    "/api/v1/admin/accounts?page=1&page_size=1000",
    "/api/admin/accounts?page=1&page_size=1000",
)


@dataclass
class Sub2APIProbe:
    ok: bool
    status: str
    message: str
    accounts_path: str | None = None
    version: str | None = None
    sample_count: int = 0
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class Sub2APICheckTarget:
    source_account: Account
    source_item: AccountItem | None
    lookup_account: Any
    display_no: str
    known_remote_id: str | None = None


def _normalize_base_url(base_url: str) -> str:
    value = base_url.strip()
    if not value.endswith("/"):
        value += "/"
    return value


def _headers(admin_key: str) -> dict[str, str]:
    return {
        "x-api-key": admin_key,
        "Accept": "application/json",
    }


def _extract_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    data = _extract_data(payload)
    if isinstance(data, dict):
        for key in ("items", "accounts", "data", "rows", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _json_or_text(response: httpx.Response) -> dict[str, Any]:
    try:
        parsed = response.json()
        return parsed if isinstance(parsed, dict) else {"data": parsed}
    except ValueError:
        return {"text": response.text[:2000]}


def probe_sub2api_instance(instance: Sub2APIInstance, timeout_seconds: int = 15) -> Sub2APIProbe:
    admin_key = field_cipher.decrypt(instance.admin_key_encrypted) or ""
    if not admin_key:
        return Sub2APIProbe(False, "missing_key", "管理员Key为空")

    base_url = _normalize_base_url(instance.base_url)
    last_error = ""
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        for path in ACCOUNTS_PATH_CANDIDATES:
            url = urljoin(base_url, path.lstrip("/"))
            try:
                response = client.get(url, headers=_headers(admin_key))
                payload = _json_or_text(response)
                if response.status_code == 200:
                    items = _extract_items(payload)
                    return Sub2APIProbe(
                        True,
                        "ok",
                        "连接成功",
                        accounts_path=path,
                        sample_count=len(items),
                        payload=payload,
                    )
                last_error = f"{path}: HTTP {response.status_code}"
                if response.status_code in {401, 403}:
                    message = str(payload.get("message") or payload.get("reason") or "管理员Key无效")
                    return Sub2APIProbe(False, "auth_failed", message, accounts_path=path, payload=payload)
            except Exception as exc:  # noqa: BLE001
                last_error = f"{path}: {exc}"

    return Sub2APIProbe(False, "not_found", last_error or "未发现可用账号接口")


def _remote_identifier(item: dict[str, Any]) -> str:
    for key in ("id", "account_id", "accountId"):
        value = item.get(key)
        if value is not None:
            return str(value)
    return ""


def _remote_name(item: dict[str, Any]) -> str:
    for key in ("name", "email", "username", "login_account", "account"):
        value = item.get(key)
        if value:
            return str(value)
    return ""


def _remote_status(item: dict[str, Any]) -> str:
    value = item.get("status")
    if value is None:
        return "unknown"
    return str(value)


def _remote_is_alive(item: dict[str, Any]) -> bool:
    status = _remote_status(item).lower()
    if status in {"active", "available", "ok", "healthy", "normal"}:
        if item.get("schedulable") is False:
            return False
        return True
    return False


def _remote_error(item: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in ("error", "last_error", "error_message", "last_error_message", "message"):
        value = item.get(key)
        if value:
            if isinstance(value, dict):
                code = value.get("code") or value.get("type") or value.get("status")
                message = value.get("message") or value.get("detail") or str(value)
                return (str(code) if code is not None else None, str(message))
            return None, str(value)
    return None, None


def _remote_rate_limit_message(item: dict[str, Any]) -> str | None:
    reset_at = item.get("rate_limit_reset_at") or item.get("overload_until") or item.get("temp_unschedulable_until")
    rate_limited_at = item.get("rate_limited_at")
    reason = item.get("temp_unschedulable_reason")
    if reset_at:
        return f"限流中，预计恢复：{reset_at}"
    if rate_limited_at:
        return f"限流中，触发时间：{rate_limited_at}"
    if item.get("schedulable") is False and reason:
        return f"暂不可调度：{reason}"
    return None


def _remote_is_rate_limited(item: dict[str, Any]) -> bool:
    if item.get("rate_limit_reset_at") or item.get("rate_limited_at") or item.get("overload_until"):
        return True
    reason = str(item.get("temp_unschedulable_reason") or "").lower()
    if item.get("schedulable") is False and any(key in reason for key in ("429", "rate", "limit", "限流")):
        return True
    return False


def _build_remote_index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        for value in (
            _remote_identifier(item),
            _remote_name(item),
            str(item.get("email") or ""),
            str(item.get("username") or ""),
        ):
            if value:
                index[value.lower()] = item
    return index


def _account_lookup_keys(
    account: Account,
    known_remote_id: str | None = None,
) -> list[str]:
    keys = [
        known_remote_id,
        account.account_no,
        account.login_account,
        account.authorized_email,
        account.bind_email,
        account.name,
    ]
    return [str(item).lower() for item in keys if item]


def _lookup_account_from_item(account: Account, item: AccountItem) -> Any:
    return SimpleNamespace(
        account_no=item.item_no,
        login_account=item.email,
        authorized_email=item.email,
        bind_email=account.bind_email,
        name=account.name,
    )


def _check_targets_for_accounts(
    accounts: list[Account],
    known_remote_ids: dict[uuid.UUID, str] | None = None,
) -> list[Sub2APICheckTarget]:
    known_remote_ids = known_remote_ids or {}
    targets: list[Sub2APICheckTarget] = []
    for account in accounts:
        details = sorted(
            list(account.items or []),
            key=lambda item: (
                item.item_index,
                item.created_at.isoformat() if item.created_at else "",
                item.item_no,
            ),
        )
        if details:
            targets.extend(
                Sub2APICheckTarget(
                    source_account=account,
                    source_item=item,
                    lookup_account=_lookup_account_from_item(account, item),
                    display_no=item.item_no,
                    known_remote_id=item.remote_account_id,
                )
                for item in details
            )
            continue
        targets.append(
            Sub2APICheckTarget(
                source_account=account,
                source_item=None,
                lookup_account=account,
                display_no=account.account_no,
                known_remote_id=known_remote_ids.get(account.id),
            )
        )
    return targets


def _survival_seconds(start: datetime | None, now: datetime) -> int | None:
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return max(0, int((now - start).total_seconds()))


def _update_account_item_check_state(
    item: AccountItem,
    now: datetime,
    *,
    is_alive: bool,
    local_status: str,
    http_status: int | None,
    error_code: str | None,
    error_message: str | None,
) -> None:
    item.status = local_status
    item.last_checked_at = now
    item.last_sub2api_status_code = http_status
    item.last_sub2api_error_code = error_code
    item.last_sub2api_message = error_message
    if is_alive:
        if item.first_seen_alive_at is None:
            item.first_seen_alive_at = now
        item.last_seen_alive_at = now
    elif item.first_abnormal_at is None:
        item.first_abnormal_at = now
    item.survival_seconds = _survival_seconds(
        item.first_seen_alive_at or item.created_at,
        now,
    )


def _select_accounts(
    db: Session,
    instance_id: uuid.UUID,
    account_type: str | None,
    import_batch_no: str | None,
    purchase_id: uuid.UUID | None,
    include_only_operation: bool,
) -> list[Account]:
    stmt = (
        select(Account)
        .where(Account.sub2api_instance_id == instance_id)
        .order_by(Account.created_at.asc())
    )
    if account_type:
        stmt = stmt.where(Account.account_type == account_type)
    if import_batch_no:
        stmt = stmt.where(Account.import_batch_no == import_batch_no)
    if purchase_id:
        stmt = stmt.where(Account.purchase_id == purchase_id)
    if include_only_operation:
        stmt = stmt.where(Account.participate_operation.is_(True))
    return db.scalars(stmt).all()


def run_admin_key_account_check(
    db: Session,
    instance: Sub2APIInstance,
    checked_by: uuid.UUID | None,
    account_type: str | None = None,
    import_batch_no: str | None = None,
    purchase_id: uuid.UUID | None = None,
    include_only_operation: bool = False,
    timeout_seconds: int = 15,
    remark: str | None = None,
) -> AccountCheckBatch:
    now = datetime.now(UTC)
    probe = probe_sub2api_instance(instance, timeout_seconds=timeout_seconds)
    instance.last_probe_at = now
    instance.last_probe_status = probe.status
    instance.last_probe_message = probe.message
    if probe.accounts_path:
        instance.detected_accounts_path = probe.accounts_path

    accounts = _select_accounts(
        db,
        instance.id,
        account_type,
        import_batch_no,
        purchase_id,
        include_only_operation,
    )
    known_remote_ids = _instance_remote_ids(
        db,
        instance.id,
        [account.id for account in accounts],
    )
    targets = _check_targets_for_accounts(accounts, known_remote_ids)
    batch = AccountCheckBatch(
        batch_no=f"SUB2-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        name=f"{instance.name} 管理员Key检测 {now.strftime('%Y-%m-%d %H:%M:%S')}",
        source="sub2api_admin",
        endpoint_url=instance.base_url,
        method="GET",
        checked_by=checked_by,
        sub2api_instance_id=instance.id,
        total_count=len(targets),
        started_at=now,
        request_config={
            "mode": "admin_key",
            "accounts_path": probe.accounts_path,
            "account_type": account_type,
            "import_batch_no": import_batch_no,
            "purchase_id": str(purchase_id) if purchase_id else None,
            "include_only_operation": include_only_operation,
        },
        remark=remark,
    )
    db.add(batch)
    db.flush()

    if not probe.ok:
        for target in targets:
            account = target.source_account
            if target.source_item is not None:
                _update_account_item_check_state(
                    target.source_item,
                    now,
                    is_alive=False,
                    local_status="check_failed" if probe.status != "auth_failed" else "api_401",
                    http_status=401 if probe.status == "auth_failed" else None,
                    error_code=probe.status,
                    error_message=probe.message,
                )
            account.last_checked_at = now
            account.last_sub2api_status_code = 401 if probe.status == "auth_failed" else None
            account.last_sub2api_error_code = probe.status
            account.last_sub2api_message = probe.message
            account.status = "check_failed" if probe.status != "auth_failed" else "api_401"
            if account.first_abnormal_at is None:
                account.first_abnormal_at = now
            batch.abnormal_count += 1
            if probe.status == "auth_failed":
                batch.status_401_count += 1
            db.add(
                AccountCheckRecord(
                    batch_id=batch.id,
                    account_id=account.id,
                    checked_at=now,
                    http_status=401 if probe.status == "auth_failed" else None,
                    sub2api_status=account.status,
                    is_alive=False,
                    error_code=probe.status,
                    error_message=probe.message,
                    raw_response=redact_raw_payload(probe.payload),
                    remark=target.display_no,
                )
            )
        batch.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(batch)
        return batch

    items = _extract_items(probe.payload)
    remote_index = _build_remote_index(items)
    for target in targets:
        account = target.source_account
        remote: dict[str, Any] | None = None
        for key in _account_lookup_keys(
            target.lookup_account,
            known_remote_id=target.known_remote_id,
        ):
            remote = remote_index.get(key)
            if remote:
                break

        if remote is None:
            is_alive = False
            local_status = "unavailable"
            error_code = "not_found_in_sub2api"
            error_message = "Sub2API账号列表中未匹配到该账号"
            raw_response: dict[str, Any] | None = None
        else:
            remote_status = _remote_status(remote)
            is_rate_limited = _remote_is_rate_limited(remote)
            is_alive = False if is_rate_limited else _remote_is_alive(remote)
            local_status = (
                "rate_limited"
                if is_rate_limited
                else "available" if is_alive else "unavailable"
            )
            error_code, error_message = _remote_error(remote)
            if is_rate_limited:
                error_code = "rate_limited"
                error_message = _remote_rate_limit_message(remote)
            elif not error_code and not is_alive:
                error_code = remote_status
            raw_response = redact_raw_payload(remote)
            remote_id = _remote_identifier(remote)
            if remote_id:
                if target.source_item is not None:
                    target.source_item.remote_account_id = remote_id
                elif not account.sub2api_account_id:
                    account.sub2api_account_id = remote_id

        if is_alive:
            if account.first_seen_alive_at is None:
                account.first_seen_alive_at = now
            if account.available_started_at is None:
                account.available_started_at = now
            account.last_seen_alive_at = now
            batch.alive_count += 1
        else:
            if account.first_abnormal_at is None:
                account.first_abnormal_at = now
            batch.abnormal_count += 1
            if local_status == "rate_limited":
                batch.status_429_count += 1

        account.status = local_status
        account.last_checked_at = now
        account.last_sub2api_status_code = 200
        account.last_sub2api_error_code = error_code
        account.last_sub2api_message = error_message
        if target.source_item is not None:
            _update_account_item_check_state(
                target.source_item,
                now,
                is_alive=is_alive,
                local_status=local_status,
                http_status=200,
                error_code=error_code,
                error_message=error_message,
            )
        start = account.first_seen_alive_at or account.available_started_at or account.created_at
        if start:
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            account.survival_seconds = max(0, int((now - start).total_seconds()))
            account.available_days = account.survival_seconds // 86400

        db.add(
            AccountCheckRecord(
                batch_id=batch.id,
                account_id=account.id,
                checked_at=now,
                http_status=200,
                sub2api_status=_remote_status(remote) if remote else "not_found",
                is_alive=is_alive,
                error_code=error_code,
                error_message=error_message,
                survived_seconds=account.survival_seconds,
                raw_response=raw_response,
                remark=target.display_no,
            )
        )

    batch.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(batch)
    return batch
