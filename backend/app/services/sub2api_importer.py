import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import field_cipher
from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.sub2api_import import Sub2APIImportBatch, Sub2APIImportItem
from app.models.sub2api_instance import Sub2APIInstance
from app.services.account_credentials import (
    SENSITIVE_RAW_KEYS,
    decrypt_raw_credentials,
    redact_raw_payload,
)


class Sub2APIImportError(RuntimeError):
    pass


class Sub2APIImportValidationError(Sub2APIImportError):
    pass


PLATFORM_ALIASES = {
    "openai": "openai",
    "codex": "openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
    "grok": "grok",
    "xai": "grok",
    "antigravity": "antigravity",
}

ACCOUNT_TYPES = {"oauth", "setup-token", "apikey", "upstream", "bedrock", "service_account"}

SUB2API_CREDENTIAL_METADATA_KEYS = {
    "account_id",
    "chatgpt_account_id",
    "chatgpt_user_id",
    "email",
    "expires_at",
    "expires_in",
    "plan_type",
    "workspace_id",
}

_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(key) for key in sorted(SENSITIVE_RAW_KEYS)) + r")\b"
    r"(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Sub2APIImportTarget:
    source_account: Account
    source_item: AccountItem | None
    payload_account: Any
    display_no: str


def _normalize_platform(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return PLATFORM_ALIASES.get(normalized, normalized)


def _has_credential_value(value: Any) -> bool:
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and "***" not in stripped and stripped != "[REDACTED]"
    if isinstance(value, dict):
        return any(_has_credential_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_credential_value(item) for item in value)
    return value is not None


def _infer_account_type(raw_type: Any, credentials: dict[str, Any]) -> str:
    normalized = str(raw_type or "").strip().lower().replace("_", "-")
    if normalized in ACCOUNT_TYPES:
        return normalized
    if credentials.get("api_key"):
        return "apikey"
    if credentials.get("setup_token"):
        return "setup-token"
    if credentials.get("service_account_json") or credentials.get("service_account"):
        return "service_account"
    if any(credentials.get(key) for key in ("access_token", "refresh_token", "session_token", "token")):
        return "oauth"
    raise Sub2APIImportValidationError("无法识别 Sub2API 凭证类型")


def _sub2api_credentials(credentials: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in credentials.items()
        if key not in SUB2API_CREDENTIAL_METADATA_KEYS
    }


def _remote_account_name(account: Account, credentials: dict[str, Any]) -> str:
    for value in (
        getattr(account, "login_account", None),
        getattr(account, "authorized_email", None),
        credentials.get("email"),
        getattr(account, "account_no", None),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(getattr(account, "account_no", "") or "").strip()


def build_sub2api_account_payload(
    account: Account,
    selected_groups: list[dict[str, Any]],
    sub2api_key: str | None,
    proxy_id: int | None = None,
) -> dict[str, Any]:
    raw = account.raw_payload if isinstance(account.raw_payload, dict) else {}
    platform = _normalize_platform(raw.get("platform") or account.account_type)
    if not platform:
        raise Sub2APIImportValidationError("无法识别账号平台")

    raw_credentials = decrypt_raw_credentials(
        getattr(account, "raw_credentials_encrypted", None)
    )
    credentials = dict(raw_credentials) if isinstance(raw_credentials, dict) else {}
    if sub2api_key and not credentials.get("api_key"):
        credentials["api_key"] = sub2api_key
    if not _has_credential_value(credentials):
        raise Sub2APIImportValidationError("账号缺少可导入的 Sub2API 凭证")

    account_type = _infer_account_type(raw.get("type"), credentials)
    remote_name = _remote_account_name(account, credentials)
    credentials = _sub2api_credentials(credentials)
    if not _has_credential_value(credentials):
        raise Sub2APIImportValidationError("璐﹀彿缂哄皯鍙鍏ョ殑 Sub2API 鍑瘉")
    group_ids = [
        int(group["id"])
        for group in selected_groups
        if not group.get("platform") or _normalize_platform(group.get("platform")) == platform
    ]
    if not group_ids:
        raise Sub2APIImportValidationError(f"账号平台 {platform} 没有匹配的目标分组")

    payload: dict[str, Any] = {
        "name": remote_name,
        "notes": account.remark or account.name,
        "platform": platform,
        "type": account_type,
        "credentials": credentials,
        "group_ids": group_ids,
        "concurrency": raw.get("concurrency") if raw.get("concurrency") is not None else 10,
        "priority": raw.get("priority") if raw.get("priority") is not None else 1,
    }
    if isinstance(raw.get("extra"), dict):
        payload["extra"] = raw["extra"]
    for field_name in ("rate_multiplier", "load_factor"):
        if raw.get(field_name) is not None:
            payload[field_name] = raw[field_name]
    if account.expired_at:
        expires_at = account.expired_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        payload["expires_at"] = int(expires_at.timestamp())
    if proxy_id is not None:
        payload["proxy_id"] = proxy_id
    return payload


def _extract_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    data = _extract_data(payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "accounts", "groups", "rows", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _extract_total(payload: Any) -> int | None:
    data = _extract_data(payload)
    for candidate in (data, payload):
        if not isinstance(candidate, dict):
            continue
        value = candidate.get("total")
        if value is not None:
            try:
                return max(int(value), 0)
            except (TypeError, ValueError):
                return None
    return None


def _response_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return _safe_error_message(response.text[:500] or f"HTTP {response.status_code}")
    payload = redact_raw_payload(payload)
    if isinstance(payload, dict):
        return _safe_error_message(
            payload.get("message") or payload.get("error") or payload.get("detail") or payload
        )
    return _safe_error_message(payload)


def _is_batch_route_misrouted_error(response: httpx.Response) -> bool:
    return response.status_code == 400 and _response_message(response) == "Invalid account ID"


def _safe_error_message(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return _SECRET_ASSIGNMENT_PATTERN.sub(
                lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
                value,
            )
    sanitized = str(redact_raw_payload(value))
    return _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        sanitized,
    )


class Sub2APIAdminClient:
    def __init__(self, instance: Sub2APIInstance, timeout_seconds: int = 30) -> None:
        self.instance = instance
        self.admin_key = field_cipher.decrypt(instance.admin_key_encrypted) or ""
        if not self.admin_key:
            raise Sub2APIImportError("Sub2API 管理员 Key 为空")
        self.base_url = instance.base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.admin_prefix = self._detected_prefix()

    def _detected_prefix(self) -> str | None:
        path = self.instance.detected_accounts_path or ""
        if "/api/v1/admin/accounts" in path:
            return "/api/v1/admin"
        if "/api/admin/accounts" in path:
            return "/api/admin"
        return None

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "x-api-key": self.admin_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _url(self, prefix: str, path: str) -> str:
        return urljoin(self.base_url, f"{prefix.strip('/')}/{path.lstrip('/')}")

    def _send_json_preserving_method(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> httpx.Response:
        response = client.request(method, url, headers=headers, json=json_body)
        for _ in range(5):
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            url = str(response.url.join(location))
            response = client.request(method, url, headers=headers, json=json_body)
        return response

    def _get_with_prefix_fallback(self, path: str) -> tuple[Any, str]:
        prefixes = [self.admin_prefix] if self.admin_prefix else []
        prefixes.extend(prefix for prefix in ("/api/v1/admin", "/api/admin") if prefix not in prefixes)
        last_error = ""
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            for prefix in prefixes:
                if prefix is None:
                    continue
                try:
                    response = client.get(self._url(prefix, path), headers=self._headers())
                except httpx.HTTPError as exc:
                    last_error = f"{prefix}: {exc}"
                    continue
                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except ValueError:
                        last_error = f"{prefix}: 返回内容不是有效 JSON"
                        continue
                    self.admin_prefix = prefix
                    return payload, prefix
                last_error = f"HTTP {response.status_code}: {_response_message(response)}"
                if response.status_code in {401, 403}:
                    break
        raise Sub2APIImportError(last_error or "Sub2API 管理接口不可用")

    def list_groups(self) -> list[dict[str, Any]]:
        payload, _ = self._get_with_prefix_fallback("groups/all")
        return _extract_items(payload)

    def list_proxies(self) -> list[dict[str, Any]]:
        payload, _ = self._get_with_prefix_fallback("proxies?page=1&page_size=1000")
        return _extract_items(payload)

    def list_accounts(self, page_size: int = 1000) -> list[dict[str, Any]]:
        page_size = max(1, min(page_size, 1000))
        page = 1
        accounts: list[dict[str, Any]] = []
        seen_page_signatures: set[str] = set()
        while True:
            payload, _ = self._get_with_prefix_fallback(
                f"accounts?page={page}&page_size={page_size}&lite=true"
            )
            page_items = _extract_items(payload)
            page_signature = json.dumps(
                page_items,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            if page_items and page_signature in seen_page_signatures:
                raise Sub2APIImportError("Sub2API 账号分页未向后推进")
            seen_page_signatures.add(page_signature)
            accounts.extend(page_items)
            total = _extract_total(payload)
            if total is not None:
                if len(accounts) >= total:
                    break
                if not page_items:
                    raise Sub2APIImportError("Sub2API 账号分页在达到总数前提前结束")
            elif not page_items or len(page_items) < page_size:
                break
            page += 1
        return accounts

    def batch_create(self, accounts: list[dict[str, Any]], idempotency_key: str) -> list[dict[str, Any]]:
        if not self.admin_prefix:
            self.list_groups()
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = self._send_json_preserving_method(
                    client,
                    "POST",
                    self._url(self.admin_prefix or "/api/v1/admin", "accounts/batch"),
                    headers=self._headers(idempotency_key),
                    json_body={"accounts": accounts},
                )
        except httpx.HTTPError as exc:
            raise Sub2APIImportError(f"Sub2API 批量创建请求失败：{exc}") from exc
        if _is_batch_route_misrouted_error(response):
            return [
                self._create_one(account, f"{idempotency_key}-{index_position}")
                for index_position, account in enumerate(accounts)
            ]
        if response.status_code not in {200, 201}:
            raise Sub2APIImportError(f"HTTP {response.status_code}: {_response_message(response)}")
        try:
            payload = _extract_data(response.json())
        except ValueError as exc:
            raise Sub2APIImportError("Sub2API 批量创建返回内容不是有效 JSON") from exc
        return payload.get("results", []) if isinstance(payload, dict) else []

    def _create_one(self, account: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        if not self.admin_prefix:
            self.list_groups()
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = self._send_json_preserving_method(
                    client,
                    "POST",
                    self._url(self.admin_prefix or "/api/v1/admin", "accounts"),
                    headers=self._headers(idempotency_key),
                    json_body=account,
                )
        except httpx.HTTPError as exc:
            return {
                "name": account.get("name"),
                "success": False,
                "error": f"Sub2API account create request failed: {exc}",
            }
        if response.status_code not in {200, 201}:
            return {
                "name": account.get("name"),
                "success": False,
                "error": f"HTTP {response.status_code}: {_response_message(response)}",
            }
        try:
            data = _extract_data(response.json())
        except ValueError:
            return {
                "name": account.get("name"),
                "success": False,
                "error": "Sub2API account create response is not valid JSON",
            }
        remote_id = _remote_identifier(data) if isinstance(data, dict) else ""
        return {
            "name": account.get("name"),
            "id": remote_id,
            "account": data if isinstance(data, dict) else {},
            "success": True,
        }

    def update_account(
        self,
        remote_id: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not self.admin_prefix:
            self.list_groups()
        update_payload = {key: value for key, value in payload.items() if key != "platform"}
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = self._send_json_preserving_method(
                    client,
                    "PUT",
                    self._url(self.admin_prefix or "/api/v1/admin", f"accounts/{remote_id}"),
                    headers=self._headers(idempotency_key),
                    json_body=update_payload,
                )
        except httpx.HTTPError as exc:
            raise Sub2APIImportError(f"Sub2API 账号更新请求失败：{exc}") from exc
        if response.status_code not in {200, 201}:
            raise Sub2APIImportError(f"HTTP {response.status_code}: {_response_message(response)}")
        try:
            data = _extract_data(response.json())
        except ValueError as exc:
            raise Sub2APIImportError("Sub2API 账号更新返回内容不是有效 JSON") from exc
        return data if isinstance(data, dict) else {}


def fetch_sub2api_groups(instance: Sub2APIInstance) -> list[dict[str, Any]]:
    return Sub2APIAdminClient(instance).list_groups()


def fetch_sub2api_proxies(instance: Sub2APIInstance) -> list[dict[str, Any]]:
    return Sub2APIAdminClient(instance).list_proxies()


def _remote_identifier(item: dict[str, Any]) -> str:
    for key in ("id", "account_id", "accountId"):
        if item.get(key) is not None:
            return str(item[key])
    return ""


RemoteAccountIndex = dict[tuple[str, str, str], list[dict[str, Any]]]


def _remote_index(items: list[dict[str, Any]]) -> RemoteAccountIndex:
    index: RemoteAccountIndex = {}
    for item in items:
        platform = _normalize_platform(item.get("platform"))
        if not platform:
            continue
        nested_credentials = (
            item.get("credentials") if isinstance(item.get("credentials"), dict) else {}
        )
        fields = [
            ("id", next(
                (item.get(key) for key in ("id", "account_id", "accountId") if item.get(key) is not None),
                None,
            )),
            ("name", item.get("name")),
            ("email", item.get("email")),
            ("email", nested_credentials.get("email")),
            ("username", item.get("username")),
            ("username", nested_credentials.get("username")),
        ]
        for field_name, value in fields:
            normalized = str(value).strip().lower() if value is not None else ""
            if normalized:
                index.setdefault((platform, field_name, normalized), []).append(item)
    return index


def _find_remote(
    account: Account,
    index: RemoteAccountIndex,
    platform: str,
    known_remote_id: str | None = None,
) -> dict[str, Any] | None:
    normalized_platform = _normalize_platform(platform)
    lookups = [
        ("id", known_remote_id),
        ("name", account.account_no),
        ("email", account.authorized_email),
    ]
    if account.login_account:
        login_field = "email" if "@" in account.login_account else "username"
        lookups.append((login_field, account.login_account))

    matches: dict[tuple[str, str], dict[str, Any]] = {}
    for field_name, value in lookups:
        normalized = str(value).strip().lower() if value is not None else ""
        if not normalized:
            continue
        for candidate in index.get((normalized_platform, field_name, normalized), []):
            remote_id = _remote_identifier(candidate)
            identity = ("id", remote_id) if remote_id else ("object", str(id(candidate)))
            matches[identity] = candidate

    if len(matches) > 1:
        raise Sub2APIImportValidationError("本地账号匹配到多个远端账号，无法安全更新")
    return next(iter(matches.values()), None)


def _finish_batch(batch: Sub2APIImportBatch, now: datetime) -> None:
    batch.success_count = sum(item.status == "success" for item in batch.items)
    batch.failed_count = sum(item.status == "failed" for item in batch.items)
    batch.skipped_count = sum(item.status == "skipped" for item in batch.items)
    if batch.failed_count == 0:
        batch.status = "completed"
    elif batch.success_count or batch.skipped_count:
        batch.status = "partial"
    else:
        batch.status = "failed"
    batch.finished_at = now


def _bind_account_to_sub2api_instance(
    account: Account,
    item: Sub2APIImportItem,
    instance_id: uuid.UUID,
    remote_account_id: str | None,
) -> None:
    normalized_remote_id = str(remote_account_id).strip() if remote_account_id else ""
    account.sub2api_instance_id = instance_id
    item.remote_account_id = normalized_remote_id or None
    if normalized_remote_id:
        account.sub2api_account_id = normalized_remote_id


def _payload_account_from_item(account: Account, item: AccountItem) -> Any:
    return SimpleNamespace(
        id=account.id,
        account_no=item.item_no,
        name=account.name,
        account_type=item.platform or account.account_type,
        remark=item.remark or account.remark,
        expired_at=account.expired_at,
        raw_payload=item.raw_payload,
        raw_credentials_encrypted=item.raw_credentials_encrypted,
        sub2api_key_encrypted=account.sub2api_key_encrypted,
        sub2api_account_id=item.remote_account_id,
        login_account=item.email,
        authorized_email=item.email,
    )


def _import_targets_for_accounts(accounts: list[Account]) -> list[Sub2APIImportTarget]:
    targets: list[Sub2APIImportTarget] = []
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
                Sub2APIImportTarget(
                    source_account=account,
                    source_item=item,
                    payload_account=_payload_account_from_item(account, item),
                    display_no=item.item_no,
                )
                for item in details
            )
            continue
        targets.append(
            Sub2APIImportTarget(
                source_account=account,
                source_item=None,
                payload_account=account,
                display_no=account.account_no,
            )
        )
    return targets


def _bind_import_target_to_sub2api_instance(
    target: Sub2APIImportTarget,
    item: Sub2APIImportItem,
    instance_id: uuid.UUID,
    remote_account_id: str | None,
) -> None:
    normalized_remote_id = str(remote_account_id).strip() if remote_account_id else ""
    target.source_account.sub2api_instance_id = instance_id
    item.remote_account_id = normalized_remote_id or None
    if normalized_remote_id:
        if target.source_item is not None:
            target.source_item.remote_account_id = normalized_remote_id
        else:
            target.source_account.sub2api_account_id = normalized_remote_id


def recover_stale_import_batch(
    batch: Sub2APIImportBatch,
    now: datetime | None = None,
    stale_after: timedelta = timedelta(minutes=15),
) -> bool:
    if batch.status != "running" or batch.started_at is None:
        return False
    current_time = now or datetime.now(UTC)
    started_at = batch.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    if current_time - started_at < stale_after:
        return False
    for item in batch.items:
        if item.status == "pending":
            item.status = "failed"
            item.error_message = "导入执行中断，可重新发起失败项重试"
    _finish_batch(batch, current_time)
    return True


def _lock_batch_for_execution(db: Session, batch: Sub2APIImportBatch) -> None:
    db.refresh(batch, with_for_update=True)


def _instance_remote_ids(
    db: Session,
    instance_id: uuid.UUID,
    account_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not account_ids:
        return {}
    rows = db.execute(
        select(Sub2APIImportItem.account_id, Sub2APIImportItem.remote_account_id)
        .join(
            Sub2APIImportBatch,
            Sub2APIImportBatch.id == Sub2APIImportItem.batch_id,
        )
        .where(
            Sub2APIImportBatch.instance_id == instance_id,
            Sub2APIImportItem.account_id.in_(account_ids),
            Sub2APIImportItem.status.in_(["success", "skipped"]),
            Sub2APIImportItem.remote_account_id.is_not(None),
        )
        .order_by(
            Sub2APIImportItem.attempted_at.desc(),
            Sub2APIImportItem.created_at.desc(),
        )
    ).all()
    result: dict[uuid.UUID, str] = {}
    for account_id, remote_account_id in rows:
        if remote_account_id is not None:
            result.setdefault(account_id, str(remote_account_id))
    return result


def run_sub2api_import(
    db: Session,
    instance: Sub2APIInstance,
    accounts: list[Account],
    group_ids: list[int],
    duplicate_policy: str,
    created_by: uuid.UUID | None,
    remark: str | None = None,
    retry_of_batch_id: uuid.UUID | None = None,
    proxy_id: int | None = None,
) -> Sub2APIImportBatch:
    now = datetime.now(UTC)
    targets = _import_targets_for_accounts(accounts)
    batch = Sub2APIImportBatch(
        batch_no=f"S2IMP-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        instance_id=instance.id,
        created_by=created_by,
        retry_of_batch_id=retry_of_batch_id,
        group_ids=group_ids,
        duplicate_policy=duplicate_policy,
        status="running",
        total_count=len(targets),
        started_at=now,
        remark=remark,
    )
    db.add(batch)
    db.flush()
    import_items: list[tuple[Sub2APIImportTarget, Sub2APIImportItem]] = []
    for target in targets:
        item = Sub2APIImportItem(
            batch_id=batch.id,
            account_id=target.source_account.id,
            action="create",
            status="pending",
            attempted_at=now,
        )
        db.add(item)
        batch.items.append(item)
        import_items.append((target, item))
    db.commit()
    _lock_batch_for_execution(db, batch)

    client: Sub2APIAdminClient | None = None
    try:
        client = Sub2APIAdminClient(instance)
        all_groups = client.list_groups()
        selected_groups = [group for group in all_groups if int(group.get("id", -1)) in group_ids]
        missing_group_ids = sorted(set(group_ids) - {int(group.get("id", -1)) for group in selected_groups})
        if missing_group_ids:
            raise Sub2APIImportError(f"Sub2API 分组不存在：{missing_group_ids}")
        remote_accounts = client.list_accounts()
        index = _remote_index(remote_accounts)
        known_remote_ids = _instance_remote_ids(
            db,
            instance.id,
            [account.id for account in accounts],
        )
    except Exception as exc:  # noqa: BLE001
        for item in batch.items:
            item.status = "failed"
            item.error_message = _safe_error_message(exc)
        _finish_batch(batch, datetime.now(UTC))
        db.commit()
        db.refresh(batch)
        return batch

    creates: list[tuple[Sub2APIImportTarget, Sub2APIImportItem, dict[str, Any]]] = []
    for target, item in import_items:
        try:
            payload = build_sub2api_account_payload(
                target.payload_account,
                selected_groups,
                field_cipher.decrypt(target.source_account.sub2api_key_encrypted),
                proxy_id=proxy_id,
            )
            known_remote_id = (
                target.source_item.remote_account_id
                if target.source_item is not None
                else known_remote_ids.get(target.source_account.id)
            )
            remote = _find_remote(
                target.payload_account,
                index,
                payload["platform"],
                known_remote_id=known_remote_id,
            )
            if remote and duplicate_policy == "skip":
                remote_id = _remote_identifier(remote)
                item.action = "skip"
                item.status = "skipped"
                _bind_import_target_to_sub2api_instance(target, item, instance.id, remote_id)
                continue
            if remote:
                remote_id = _remote_identifier(remote)
                if not remote_id:
                    raise Sub2APIImportError("远端重复账号缺少账号 ID")
                item.action = "update"
                result = client.update_account(
                    remote_id,
                    payload,
                    f"{batch.batch_no}-{target.display_no}-update",
                )
                item.status = "success"
                _bind_import_target_to_sub2api_instance(
                    target,
                    item,
                    instance.id,
                    str(result.get("id") or remote_id),
                )
                continue
            creates.append((target, item, payload))
        except Exception as exc:  # noqa: BLE001
            item.status = "failed"
            item.error_message = _safe_error_message(exc)

    if creates:
        try:
            results = client.batch_create(
                [entry[2] for entry in creates],
                f"{batch.batch_no}-create",
            )
            for index_position, (target, item, _) in enumerate(creates):
                result = results[index_position] if index_position < len(results) else {}
                if result.get("success"):
                    remote_id = str(
                        result.get("id")
                        or (result.get("account") or {}).get("id")
                        or ""
                    )
                    item.status = "success"
                    _bind_import_target_to_sub2api_instance(target, item, instance.id, remote_id)
                else:
                    item.status = "failed"
                    item.error_message = _safe_error_message(
                        result.get("error") or "Sub2API 未返回创建结果"
                    )
        except Exception as exc:  # noqa: BLE001
            for _, item, _ in creates:
                item.status = "failed"
                item.error_message = _safe_error_message(exc)

    _finish_batch(batch, datetime.now(UTC))
    db.commit()
    db.refresh(batch)
    return batch
