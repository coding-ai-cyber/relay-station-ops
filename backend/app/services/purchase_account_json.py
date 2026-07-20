import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.purchase import Purchase
from app.schemas.purchase import PurchaseAccountJsonBindItem, PurchaseAccountJsonBindResult
from app.services.account_credentials import prepare_raw_payload


def extract_purchase_json_accounts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("accounts"), list):
        items = payload["accounts"]
    elif (
        isinstance(payload, dict)
        and isinstance(payload.get("data"), dict)
        and isinstance(payload["data"].get("accounts"), list)
    ):
        items = payload["data"]["accounts"]
    else:
        raise ValueError("No accounts array found")

    if not items:
        raise ValueError("No valid accounts found")
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("accounts array contains invalid account entries")
    return items


def _credentials(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("credentials")
    return value if isinstance(value, dict) else {}


def _decode_jwt_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    parts = value.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _email_from_access_token(credentials: dict[str, Any]) -> str | None:
    payload = _decode_jwt_payload(credentials.get("access_token"))
    profile = payload.get("https://api.openai.com/profile")
    if isinstance(profile, dict) and profile.get("email"):
        return str(profile["email"])
    return None


def _email(item: dict[str, Any]) -> str | None:
    credentials = _credentials(item)
    for value in (
        credentials.get("email"),
        _email_from_access_token(credentials),
        item.get("email"),
        item.get("account"),
        item.get("username"),
    ):
        if value:
            return str(value)
    return None


def _remote_id(item: dict[str, Any]) -> str | None:
    credentials = _credentials(item)
    for value in (
        credentials.get("account_id"),
        credentials.get("chatgpt_account_id"),
        item.get("id"),
        item.get("account_id"),
    ):
        if value:
            return str(value)
    return None


def _plan_type(item: dict[str, Any]) -> str | None:
    credentials = _credentials(item)
    value = credentials.get("plan_type") or item.get("plan_type")
    return str(value) if value else None


def _sorted_accounts(accounts: list[Account]) -> list[Account]:
    return sorted(accounts, key=lambda account: account.account_no)


def _purchase_account_quantity(purchase: Purchase) -> int:
    quantity = purchase.quantity
    if quantity is None or quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("Account purchase quantity must be a positive integer")
    return int(quantity)


def _make_batch_account_asset(purchase: Purchase) -> Account:
    quantity = _purchase_account_quantity(purchase)
    unit_cost = purchase.total_price / quantity
    return Account(
        account_no=f"{purchase.purchase_no}-A001",
        name=purchase.product_name,
        supplier_id=purchase.supplier_id,
        purchase_id=purchase.id,
        account_type=purchase.product_type or "other",
        plan_type=None,
        status="pending_test",
        participate_operation=False,
        include_real_cost=purchase.include_real_cost,
        cost_unit_price=unit_cost,
        raw_payload={
            "source": "purchase_json_auto_asset_generation",
            "purchase_no": purchase.purchase_no,
            "purchase_quantity": str(purchase.quantity),
            "asset_index": 1,
            "note": "Account asset auto-generated before JSON binding",
        },
        remark=f"Auto-generated from JSON binding for purchase {purchase.purchase_no}",
    )


def _validate_json_accounts_have_importable_credentials(json_accounts: list[dict[str, Any]]) -> None:
    invalid_indexes: list[int] = []
    for index, item in enumerate(json_accounts, start=1):
        _, encrypted = prepare_raw_payload(item)
        if not encrypted:
            invalid_indexes.append(index)
    if invalid_indexes:
        raise ValueError(
            "JSON account entries without importable credentials: "
            + ", ".join(str(index) for index in invalid_indexes)
        )


def bind_json_items_to_accounts(
    purchase: Purchase,
    accounts: list[Account],
    json_accounts: list[dict[str, Any]],
    import_batch_no: str,
    file_id: uuid.UUID | None,
    overwrite_existing: bool,
    remark: str | None,
    account_items: list[AccountItem] | None = None,
    account_type: str | None = None,
    plan_type: str | None = None,
) -> PurchaseAccountJsonBindResult:
    ordered_accounts = _sorted_accounts(accounts)
    if account_items is not None:
        if not ordered_accounts:
            raise ValueError("No account asset available for this purchase")
        if account_items and not overwrite_existing:
            raise ValueError("Account details already exist for this purchase")
        return _bind_json_items_to_account_details(
            purchase=purchase,
            account=ordered_accounts[0],
            account_items=account_items,
            json_accounts=json_accounts,
            import_batch_no=import_batch_no,
            file_id=file_id,
            overwrite_existing=overwrite_existing,
            remark=remark,
            account_type=account_type,
            plan_type=plan_type,
        )

    if len(json_accounts) > len(ordered_accounts):
        raise ValueError("JSON account count exceeds purchase account asset count")

    available_accounts = (
        ordered_accounts
        if overwrite_existing
        else [account for account in ordered_accounts if not account.raw_credentials_encrypted]
    )
    if available_accounts and len(json_accounts) > len(available_accounts):
        raise ValueError("JSON account count exceeds remaining unbound account assets")

    result = PurchaseAccountJsonBindResult(
        purchase_id=purchase.id,
        import_batch_no=import_batch_no,
        total_json_accounts=len(json_accounts),
    )

    for index, item in enumerate(json_accounts):
        if index >= len(available_accounts):
            result.skipped_count += 1
            result.items.append(
                PurchaseAccountJsonBindItem(
                    email=_email(item),
                    status="skipped",
                    message="No unbound account asset available",
                )
            )
            continue

        account = available_accounts[index]
        sanitized, encrypted = prepare_raw_payload(
            item,
            existing_encrypted=account.raw_credentials_encrypted,
        )
        email = _email(item)
        if not encrypted:
            result.skipped_count += 1
            result.items.append(
                PurchaseAccountJsonBindItem(
                    account_id=account.id,
                    account_no=account.account_no,
                    email=email,
                    status="skipped",
                    message="Account entry has no importable credentials",
                )
            )
            continue

        account.raw_payload = sanitized
        account.raw_credentials_encrypted = encrypted
        account.login_account = email
        account.authorized_email = email
        account.sub2api_account_id = _remote_id(item)
        account.account_type = account_type or str(item.get("platform") or account.account_type or "other")
        account.plan_type = plan_type or _plan_type(item)
        account.import_file_id = file_id
        account.import_batch_no = import_batch_no
        if remark:
            account.remark = remark
        result.bound_count += 1
        result.items.append(
            PurchaseAccountJsonBindItem(
                account_id=account.id,
                account_no=account.account_no,
                email=email,
                status="bound",
                message="Bound JSON credentials",
            )
        )
    return result


def _bind_json_items_to_account_details(
    purchase: Purchase,
    account: Account,
    account_items: list[AccountItem],
    json_accounts: list[dict[str, Any]],
    import_batch_no: str,
    file_id: uuid.UUID | None,
    overwrite_existing: bool,
    remark: str | None,
    account_type: str | None = None,
    plan_type: str | None = None,
) -> PurchaseAccountJsonBindResult:
    del file_id, overwrite_existing
    result = PurchaseAccountJsonBindResult(
        purchase_id=purchase.id,
        import_batch_no=import_batch_no,
        total_json_accounts=len(json_accounts),
    )

    first_bound_item: AccountItem | None = None
    for index, item in enumerate(json_accounts, start=1):
        sanitized, encrypted = prepare_raw_payload(item)
        email = _email(item)
        if not encrypted:
            result.skipped_count += 1
            result.items.append(
                PurchaseAccountJsonBindItem(
                    account_id=account.id,
                    account_no=f"{account.account_no}-D{index:03d}",
                    email=email,
                    status="skipped",
                    message="Account entry has no importable credentials",
                )
            )
            continue

        detail = AccountItem(
            account_id=account.id,
            purchase_id=purchase.id,
            item_no=f"{account.account_no}-D{index:03d}",
            item_index=index,
            email=email,
            platform=account_type or str(item.get("platform") or account.account_type or "other"),
            plan_type=plan_type or _plan_type(item),
            remote_account_id=_remote_id(item),
            status="bound",
            import_batch_no=import_batch_no,
            raw_payload=sanitized,
            raw_credentials_encrypted=encrypted,
            remark=remark,
        )
        account_items.append(detail)
        first_bound_item = first_bound_item or detail
        result.bound_count += 1
        result.items.append(
            PurchaseAccountJsonBindItem(
                account_id=account.id,
                account_no=detail.item_no,
                email=email,
                status="bound",
                message="Bound JSON credentials as account detail",
            )
        )

    if first_bound_item is not None:
        account.raw_payload = {
            "source": "purchase_account_details",
            "purchase_no": purchase.purchase_no,
            "purchase_quantity": str(purchase.quantity),
            "detail_count": result.bound_count,
            "import_batch_no": import_batch_no,
        }
        account.raw_credentials_encrypted = first_bound_item.raw_credentials_encrypted
        account.login_account = first_bound_item.email
        account.authorized_email = first_bound_item.email
        if account_type:
            account.account_type = account_type
        if plan_type:
            account.plan_type = plan_type
        account.import_batch_no = import_batch_no
        if remark:
            account.remark = remark
    return result


def bind_purchase_account_json(
    db: Session,
    purchase: Purchase,
    payload: Any,
    file_id: uuid.UUID | None,
    overwrite_existing: bool,
    remark: str | None,
    account_type: str | None = None,
    plan_type: str | None = None,
) -> PurchaseAccountJsonBindResult:
    json_accounts = extract_purchase_json_accounts(payload)
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.purchase_id == purchase.id)
            .order_by(Account.account_no.asc())
        ).all()
    )
    if not accounts:
        account = _make_batch_account_asset(purchase)
        accounts = [account]
        db.add_all(accounts)
    account_items = list(
        db.scalars(
            select(AccountItem)
            .where(AccountItem.purchase_id == purchase.id)
            .order_by(AccountItem.item_index.asc())
        ).all()
    )
    if account_items and overwrite_existing:
        _validate_json_accounts_have_importable_credentials(json_accounts)
        for item in account_items:
            db.delete(item)
        db.flush()
        account_items = []
    import_batch_no = f"JSON-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    result = bind_json_items_to_accounts(
        purchase=purchase,
        accounts=accounts,
        json_accounts=json_accounts,
        import_batch_no=import_batch_no,
        file_id=file_id,
        overwrite_existing=overwrite_existing,
        remark=remark,
        account_items=account_items,
        account_type=account_type,
        plan_type=plan_type,
    )
    db.add_all(account_items)
    db.commit()
    return result
