# Purchase Account JSON Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a purchase-centered workflow that generates one account asset per purchased account, binds multi-account Sub2API JSON credentials to those assets, imports them to Sub2API groups, and monitors survival time by purchase batch.

**Architecture:** Keep `Purchase` as the business batch root and `Account` as the per-account operating asset. Add a focused JSON binding service and purchase route endpoint; reuse existing account credential encryption, Sub2API import, and Sub2API check services. Frontend changes stay in `PurchasesPage.tsx` and shared API type/endpoint files, with the existing `AccountsPage.tsx` flow left intact.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic-free model reuse, pytest/unittest, React, TypeScript, Ant Design, TanStack Query, Vite.

## Global Constraints

- Sensitive JSON fields such as `credentials`, `access_token`, `refresh_token`, and `api_key` must only be stored encrypted or shown redacted.
- The first implementation uses order-based binding from JSON `accounts[]` to unbound purchase account assets.
- Do not introduce background scheduling; status checks remain user-triggered.
- Reuse `prepare_raw_payload`, `run_sub2api_import`, and `run_admin_key_account_check` instead of duplicating credential or Sub2API logic.
- The current workspace has an empty `.git` directory, so commit commands may fail until Git metadata is restored.

---

## File Structure

- Modify `backend/app/api/routes/purchases.py`: generate multiple account assets and expose the JSON binding endpoint.
- Modify `backend/app/schemas/purchase.py`: add binding request/result schemas and account asset summary fields.
- Create `backend/app/services/purchase_account_json.py`: parse Sub2API JSON and bind parsed entries to existing purchase assets.
- Modify `backend/app/schemas/account.py`: add `purchase_id` to automatic check request.
- Modify `backend/app/services/sub2api_admin_adapter.py`: filter auto checks by `purchase_id`.
- Modify `backend/app/api/routes/sub2api_imports.py` and `backend/app/schemas/sub2api_import.py`: support `purchase_id` import scope while preserving existing selected/all behavior.
- Modify `frontend/src/api/types.ts`: add binding result types and request fields.
- Modify `frontend/src/api/endpoints.ts`: add binding endpoint and purchase-scoped import/check request helpers.
- Modify `frontend/src/pages/PurchasesPage.tsx`: add upload/bind/import/check actions for account purchases.
- Test `backend/tests/test_purchase_dashboard_features.py`: update multi-asset generation tests.
- Create `backend/tests/test_purchase_account_json_binding.py`: parser and binding behavior.
- Modify `backend/tests/test_sub2api_import_routes.py`: purchase-scoped import resolution.
- Modify `backend/tests/test_sub2api_admin_adapter.py`: purchase-scoped auto check filtering.

---

### Task 1: Generate One Account Asset Per Purchased Account

**Files:**
- Modify: `backend/app/api/routes/purchases.py`
- Modify: `backend/app/schemas/purchase.py`
- Test: `backend/tests/test_purchase_dashboard_features.py`

**Interfaces:**
- Produces: `_make_account_assets_from_purchase(purchase: Purchase) -> list[Account]`
- Produces: `PurchaseAssetGenerationResult.created_accounts` equal to generated account count
- Consumes: existing `Purchase.quantity`, `Purchase.total_price`, `Account.purchase_id`

- [ ] **Step 1: Write the failing unit tests**

Replace the existing `test_account_purchase_generates_one_combined_asset` in `backend/tests/test_purchase_dashboard_features.py` with:

```python
    def test_account_purchase_generates_one_asset_per_quantity(self):
        purchase_id = uuid.uuid4()
        purchase = Purchase(
            id=purchase_id,
            purchase_no="PO-20260715-B3CWWP",
            purchase_type="account",
            product_name="20 account JSON bundle",
            product_type="openai",
            quantity=Decimal("3"),
            unit_price=Decimal("0.60"),
            total_price=Decimal("1.80"),
            currency="CNY",
            purchased_at=date(2026, 7, 15),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="valid",
        )

        accounts = _make_account_assets_from_purchase(purchase)

        self.assertEqual([item.account_no for item in accounts], [
            "PO-20260715-B3CWWP-A001",
            "PO-20260715-B3CWWP-A002",
            "PO-20260715-B3CWWP-A003",
        ])
        self.assertTrue(all(item.purchase_id == purchase_id for item in accounts))
        self.assertTrue(all(item.account_type == "openai" for item in accounts))
        self.assertTrue(all(item.cost_unit_price == Decimal("0.60") for item in accounts))
        self.assertTrue(all(item.raw_payload["source"] == "purchase_asset_generation" for item in accounts))

    def test_account_purchase_rejects_fractional_quantity_for_assets(self):
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260715-FRACTN",
            purchase_type="account",
            product_name="fractional bundle",
            quantity=Decimal("1.5"),
            unit_price=Decimal("1"),
            total_price=Decimal("1.5"),
            currency="CNY",
            purchased_at=date(2026, 7, 15),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="valid",
        )

        with self.assertRaises(ValueError):
            _make_account_assets_from_purchase(purchase)
```

Update the import line:

```python
from app.api.routes.purchases import _make_account_assets_from_purchase, generate_purchase_no
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_dashboard_features.py::PurchaseAssetStatusTests -v
```

Expected: FAIL because `_make_account_assets_from_purchase` is not defined.

- [ ] **Step 3: Implement multi-account asset generation**

In `backend/app/api/routes/purchases.py`, replace `_make_account_asset_from_purchase` with:

```python
def _purchase_account_quantity(purchase: Purchase) -> int:
    quantity = purchase.quantity
    if quantity is None or quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("Account purchase quantity must be a positive integer")
    return int(quantity)


def _make_account_assets_from_purchase(purchase: Purchase) -> list[Account]:
    quantity = _purchase_account_quantity(purchase)
    unit_cost = purchase.total_price / quantity
    return [
        Account(
            account_no=f"{purchase.purchase_no}-A{index:03d}",
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
                "source": "purchase_asset_generation",
                "purchase_no": purchase.purchase_no,
                "purchase_quantity": str(purchase.quantity),
                "asset_index": index,
                "note": "Account asset generated from one purchase record",
            },
            remark=f"Generated from purchase {purchase.purchase_no}",
        )
        for index in range(1, quantity + 1)
    ]
```

In `create_assets_from_purchase`, replace:

```python
        account = _make_account_asset_from_purchase(purchase)
        db.add(account)
        result.created_accounts = 1
```

with:

```python
        try:
            accounts = _make_account_assets_from_purchase(purchase)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        db.add_all(accounts)
        result.created_accounts = len(accounts)
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_dashboard_features.py::PurchaseAssetStatusTests -v
```

Expected: PASS.

- [ ] **Step 5: Run adjacent backend tests**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_dashboard_features.py tests/test_cost_items.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit if Git metadata is restored**

Run:

```powershell
git status --short
git add backend/app/api/routes/purchases.py backend/tests/test_purchase_dashboard_features.py
git commit -m "feat: generate purchase account assets per quantity"
```

Expected: commit succeeds only after `.git` contains valid repository metadata.

---

### Task 2: Bind Sub2API Multi-Account JSON To Purchase Assets

**Files:**
- Create: `backend/app/services/purchase_account_json.py`
- Modify: `backend/app/api/routes/purchases.py`
- Modify: `backend/app/schemas/purchase.py`
- Test: `backend/tests/test_purchase_account_json_binding.py`

**Interfaces:**
- Produces: `extract_purchase_json_accounts(payload: Any) -> list[dict[str, Any]]`
- Produces: `bind_purchase_account_json(db: Session, purchase: Purchase, payload: Any, file_id: uuid.UUID | None, overwrite_existing: bool, remark: str | None) -> PurchaseAccountJsonBindResult`
- Consumes: `prepare_raw_payload(raw_payload, existing_encrypted=None)`

- [ ] **Step 1: Add schemas**

Append to `backend/app/schemas/purchase.py`:

```python
class PurchaseAccountJsonBindRequest(BaseModel):
    file_id: uuid.UUID | None = None
    payload: dict | list
    overwrite_existing: bool = False
    remark: str | None = None


class PurchaseAccountJsonBindItem(BaseModel):
    account_id: uuid.UUID | None = None
    account_no: str | None = None
    email: str | None = None
    status: str
    message: str


class PurchaseAccountJsonBindResult(BaseModel):
    purchase_id: uuid.UUID
    import_batch_no: str
    total_json_accounts: int
    bound_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    items: list[PurchaseAccountJsonBindItem] = Field(default_factory=list)
```

- [ ] **Step 2: Write parser and binding tests**

Create `backend/tests/test_purchase_account_json_binding.py`:

```python
import unittest
import uuid
from datetime import date
from decimal import Decimal

from app.core.security import field_cipher
from app.models.account import Account
from app.models.purchase import Purchase
from app.services.account_credentials import decrypt_raw_credentials
from app.services.purchase_account_json import (
    bind_json_items_to_accounts,
    extract_purchase_json_accounts,
)


class PurchaseAccountJsonParsingTests(unittest.TestCase):
    def test_extracts_accounts_from_sub2api_root_object(self):
        payload = {"accounts": [{"name": "a"}, {"name": "b"}]}

        self.assertEqual(extract_purchase_json_accounts(payload), [{"name": "a"}, {"name": "b"}])

    def test_extracts_accounts_from_root_array(self):
        payload = [{"name": "a"}]

        self.assertEqual(extract_purchase_json_accounts(payload), [{"name": "a"}])

    def test_rejects_payload_without_accounts(self):
        with self.assertRaises(ValueError):
            extract_purchase_json_accounts({"items": []})


class PurchaseAccountJsonBindingTests(unittest.TestCase):
    def test_binds_credentials_and_email_to_existing_assets(self):
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260716-K12",
            purchase_type="account",
            product_name="K12",
            quantity=Decimal("2"),
            unit_price=Decimal("1"),
            total_price=Decimal("2"),
            currency="USDT",
            purchased_at=date(2026, 7, 16),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="testing",
        )
        accounts = [
            Account(id=uuid.uuid4(), account_no="PO-20260716-K12-A001", purchase_id=purchase.id, account_type="k12"),
            Account(id=uuid.uuid4(), account_no="PO-20260716-K12-A002", purchase_id=purchase.id, account_type="k12"),
        ]
        json_accounts = [
            {
                "name": "remote-a",
                "platform": "openai",
                "type": "oauth",
                "credentials": {
                    "access_token": "token-a",
                    "email": "a@example.com",
                    "plan_type": "plus",
                    "account_id": "remote-a-id",
                },
            }
        ]

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=accounts,
            json_accounts=json_accounts,
            import_batch_no="JSON-202607160001",
            file_id=None,
            overwrite_existing=False,
            remark="sample",
        )

        self.assertEqual(result.bound_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(accounts[0].login_account, "a@example.com")
        self.assertEqual(accounts[0].authorized_email, "a@example.com")
        self.assertEqual(accounts[0].sub2api_account_id, "remote-a-id")
        self.assertEqual(accounts[0].account_type, "openai")
        self.assertEqual(accounts[0].plan_type, "plus")
        self.assertEqual(accounts[0].raw_payload["credentials"], "[REDACTED]")
        self.assertEqual(decrypt_raw_credentials(accounts[0].raw_credentials_encrypted)["access_token"], "token-a")
        self.assertIsNone(accounts[1].login_account)

    def test_does_not_overwrite_existing_credentials_by_default(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-1", purchase_type="account")
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-1-A001",
            purchase_id=purchase.id,
            account_type="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old"}'),
        )

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            json_accounts=[{"credentials": {"access_token": "new", "email": "new@example.com"}}],
            import_batch_no="JSON-1",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(result.bound_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(decrypt_raw_credentials(account.raw_credentials_encrypted)["access_token"], "old")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_account_json_binding.py -v
```

Expected: FAIL because `app.services.purchase_account_json` is missing.

- [ ] **Step 4: Implement binding service**

Create `backend/app/services/purchase_account_json.py`:

```python
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
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
        raise ValueError("未识别到 accounts 数组")
    accounts = [item for item in items if isinstance(item, dict)]
    if not accounts:
        raise ValueError("未识别到有效账号")
    return accounts


def _credentials(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("credentials")
    return value if isinstance(value, dict) else {}


def _email(item: dict[str, Any]) -> str | None:
    credentials = _credentials(item)
    for value in (
        credentials.get("email"),
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


def bind_json_items_to_accounts(
    purchase: Purchase,
    accounts: list[Account],
    json_accounts: list[dict[str, Any]],
    import_batch_no: str,
    file_id: uuid.UUID | None,
    overwrite_existing: bool,
    remark: str | None,
) -> PurchaseAccountJsonBindResult:
    available_accounts = [
        account for account in accounts if overwrite_existing or not account.raw_credentials_encrypted
    ]
    result = PurchaseAccountJsonBindResult(
        purchase_id=purchase.id,
        import_batch_no=import_batch_no,
        total_json_accounts=len(json_accounts),
    )
    if len(json_accounts) > len(available_accounts):
        raise ValueError("JSON 账号数量超过可绑定账号资产数量")

    for index, item in enumerate(json_accounts):
        account = available_accounts[index]
        if account.raw_credentials_encrypted and not overwrite_existing:
            result.skipped_count += 1
            result.items.append(
                PurchaseAccountJsonBindItem(
                    account_id=account.id,
                    account_no=account.account_no,
                    email=_email(item),
                    status="skipped",
                    message="账号资产已有凭据，未覆盖",
                )
            )
            continue
        sanitized, encrypted = prepare_raw_payload(
            item,
            existing_encrypted=account.raw_credentials_encrypted,
        )
        email = _email(item)
        account.raw_payload = sanitized
        account.raw_credentials_encrypted = encrypted
        account.login_account = email
        account.authorized_email = email
        account.sub2api_account_id = _remote_id(item)
        account.account_type = str(item.get("platform") or account.account_type or "other")
        account.plan_type = _plan_type(item)
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
                message="已绑定 JSON 凭据",
            )
        )
    return result


def bind_purchase_account_json(
    db: Session,
    purchase: Purchase,
    payload: Any,
    file_id: uuid.UUID | None,
    overwrite_existing: bool,
    remark: str | None,
) -> PurchaseAccountJsonBindResult:
    json_accounts = extract_purchase_json_accounts(payload)
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.purchase_id == purchase.id)
            .order_by(Account.account_no.asc())
        ).all()
    )
    import_batch_no = f"JSON-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    result = bind_json_items_to_accounts(
        purchase=purchase,
        accounts=accounts,
        json_accounts=json_accounts,
        import_batch_no=import_batch_no,
        file_id=file_id,
        overwrite_existing=overwrite_existing,
        remark=remark,
    )
    db.commit()
    return result
```

- [ ] **Step 5: Add route endpoint**

In `backend/app/api/routes/purchases.py`, add imports:

```python
    PurchaseAccountJsonBindRequest,
    PurchaseAccountJsonBindResult,
```

and:

```python
from app.services.purchase_account_json import bind_purchase_account_json
```

Append route:

```python
@router.post("/{purchase_id}/accounts/bind-json", response_model=PurchaseAccountJsonBindResult)
def bind_purchase_accounts_json(
    purchase_id: uuid.UUID,
    payload: PurchaseAccountJsonBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)),
) -> PurchaseAccountJsonBindResult:
    del current_user
    purchase = _get_purchase_or_404(db, purchase_id)
    if purchase.purchase_type != "account":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only account purchases can bind account JSON")
    try:
        return bind_purchase_account_json(
            db=db,
            purchase=purchase,
            payload=payload.payload,
            file_id=payload.file_id,
            overwrite_existing=payload.overwrite_existing,
            remark=payload.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_account_json_binding.py tests/test_account_credentials.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit if Git metadata is restored**

Run:

```powershell
git status --short
git add backend/app/services/purchase_account_json.py backend/app/api/routes/purchases.py backend/app/schemas/purchase.py backend/tests/test_purchase_account_json_binding.py
git commit -m "feat: bind purchase account json credentials"
```

Expected: commit succeeds only after `.git` contains valid repository metadata.

---

### Task 3: Add Purchase Scope To Sub2API Import And Auto Check

**Files:**
- Modify: `backend/app/schemas/sub2api_import.py`
- Modify: `backend/app/api/routes/sub2api_imports.py`
- Modify: `backend/app/schemas/account.py`
- Modify: `backend/app/services/sub2api_admin_adapter.py`
- Test: `backend/tests/test_sub2api_import_routes.py`
- Test: `backend/tests/test_sub2api_admin_adapter.py`

**Interfaces:**
- Consumes: `purchase_id` from `Sub2APIImportCreate`
- Consumes: `purchase_id` from `Sub2APIAutoCheckRequest`
- Produces: import/check queries limited to accounts from the selected purchase

- [ ] **Step 1: Update `Sub2APIImportCreate` tests**

In `backend/tests/test_sub2api_import_routes.py`, add a test near request validation tests:

```python
def test_accepts_purchase_scope_without_account_ids():
    payload = Sub2APIImportCreate(
        instance_id=uuid.uuid4(),
        purchase_id=uuid.uuid4(),
        group_ids=[1],
    )

    assert payload.purchase_id is not None
    assert payload.account_ids == []
    assert payload.select_all is False
```

- [ ] **Step 2: Update import schema**

In `backend/app/schemas/sub2api_import.py`, add:

```python
purchase_id: uuid.UUID | None = None
```

to `Sub2APIImportCreate`, and update its validator so exactly one of these scopes is used:

```python
scopes = [
    bool(self.select_all),
    bool(self.account_ids),
    self.purchase_id is not None,
]
if sum(scopes) != 1:
    raise ValueError("Select exactly one import scope")
```

- [ ] **Step 3: Update import account resolution**

In `backend/app/api/routes/sub2api_imports.py`, update `_resolve_import_accounts`:

```python
def _resolve_import_accounts(db: Session, payload: Sub2APIImportCreate) -> list[Account]:
    if payload.purchase_id:
        accounts = list(
            db.scalars(
                select(Account)
                .where(Account.purchase_id == payload.purchase_id)
                .order_by(Account.account_no.asc())
            ).all()
        )
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No accounts available for this purchase",
            )
        return accounts
    if payload.select_all:
        accounts = list(db.scalars(select(Account).order_by(Account.created_at.desc())).all())
        if not accounts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No accounts available to import")
        return accounts
    return _accounts_in_order(db, list(dict.fromkeys(payload.account_ids)))
```

- [ ] **Step 4: Add purchase filter to auto checks**

In `backend/app/schemas/account.py`, add:

```python
purchase_id: uuid.UUID | None = None
```

to `Sub2APIAutoCheckRequest`.

In `backend/app/services/sub2api_admin_adapter.py`, locate the account selection query and add:

```python
if purchase_id:
    stmt = stmt.where(Account.purchase_id == purchase_id)
```

Also add `purchase_id: uuid.UUID | None = None` to `run_admin_key_account_check(...)` and pass `payload.purchase_id` from `backend/app/api/routes/accounts.py`.

- [ ] **Step 5: Run backend route/service tests**

Run:

```powershell
cd backend
python -m pytest tests/test_sub2api_import_routes.py tests/test_sub2api_admin_adapter.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit if Git metadata is restored**

Run:

```powershell
git status --short
git add backend/app/schemas/sub2api_import.py backend/app/api/routes/sub2api_imports.py backend/app/schemas/account.py backend/app/services/sub2api_admin_adapter.py backend/app/api/routes/accounts.py backend/tests/test_sub2api_import_routes.py backend/tests/test_sub2api_admin_adapter.py
git commit -m "feat: scope sub2api operations by purchase"
```

Expected: commit succeeds only after `.git` contains valid repository metadata.

---

### Task 4: Add Purchase Page JSON Bind, Import, And Check Actions

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/pages/PurchasesPage.tsx`

**Interfaces:**
- Produces: `bindPurchaseAccountJson(purchaseId: string, payload: PurchaseAccountJsonBindRequest)`
- Produces: `createSub2ApiImport({ purchase_id, ... })`
- Produces: `runAutoSub2ApiAccountCheck({ purchase_id, instance_id, ... })`
- Consumes: existing `uploadFile`, `listSub2ApiInstances`, `listSub2ApiGroups`, `createSub2ApiImport`, `runAutoSub2ApiAccountCheck`

- [ ] **Step 1: Add frontend types**

In `frontend/src/api/types.ts`, add:

```ts
export type PurchaseAccountJsonBindItem = {
  account_id?: string | null;
  account_no?: string | null;
  email?: string | null;
  status: string;
  message: string;
};

export type PurchaseAccountJsonBindResult = {
  purchase_id: string;
  import_batch_no: string;
  total_json_accounts: number;
  bound_count: number;
  skipped_count: number;
  failed_count: number;
  items: PurchaseAccountJsonBindItem[];
};

export type PurchaseAccountJsonBindRequest = {
  file_id?: string | null;
  payload: Record<string, unknown> | Record<string, unknown>[];
  overwrite_existing: boolean;
  remark?: string | null;
};
```

Extend `Sub2APIImportCreateRequest`:

```ts
purchase_id?: string;
```

- [ ] **Step 2: Add endpoint**

In `frontend/src/api/endpoints.ts`, import the new types and add:

```ts
export async function bindPurchaseAccountJson(
  purchaseId: string,
  payload: PurchaseAccountJsonBindRequest
) {
  return apiRequest<PurchaseAccountJsonBindResult>(
    `/api/purchases/${purchaseId}/accounts/bind-json`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}
```

- [ ] **Step 3: Add state and mutations in `PurchasesPage.tsx`**

Add imports:

```ts
import {
  CloudUploadOutlined,
  BuildOutlined,
  EditOutlined,
  FileSearchOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  UploadOutlined
} from "@ant-design/icons";
```

Add endpoint imports:

```ts
  bindPurchaseAccountJson,
  createSub2ApiImport,
  listSub2ApiGroups,
  listSub2ApiInstances,
  runAutoSub2ApiAccountCheck,
```

Add state:

```ts
const [jsonBindPurchase, setJsonBindPurchase] = useState<Purchase | null>(null);
const [sub2apiPurchase, setSub2apiPurchase] = useState<Purchase | null>(null);
const [checkPurchase, setCheckPurchase] = useState<Purchase | null>(null);
const [jsonBindForm] = Form.useForm();
const [sub2apiForm] = Form.useForm();
const [checkForm] = Form.useForm();
```

Add queries:

```ts
const instancesQuery = useQuery({ queryKey: ["sub2api-instances"], queryFn: listSub2ApiInstances });
const selectedInstanceId = Form.useWatch("instance_id", sub2apiForm) as string | undefined;
const groupsQuery = useQuery({
  queryKey: ["sub2api-groups", selectedInstanceId],
  queryFn: () => listSub2ApiGroups(selectedInstanceId!),
  enabled: !!selectedInstanceId && !!sub2apiPurchase
});
```

- [ ] **Step 4: Implement upload bind mutation**

Add:

```ts
const bindJsonMutation = useMutation({
  mutationFn: async (values: Record<string, unknown>) => {
    const file = values.file as File | undefined;
    if (!jsonBindPurchase || !file) {
      throw new Error("请选择要绑定的 JSON 文件");
    }
    const [uploaded, text] = await Promise.all([uploadFile(file), file.text()]);
    const payload = JSON.parse(text) as Record<string, unknown> | Record<string, unknown>[];
    return bindPurchaseAccountJson(jsonBindPurchase.id, {
      file_id: uploaded.id,
      payload,
      overwrite_existing: Boolean(values.overwrite_existing),
      remark: values.remark ? String(values.remark) : undefined
    });
  },
  onSuccess: async (result) => {
    message.success(`已绑定 ${result.bound_count} 个账号，跳过 ${result.skipped_count} 个`);
    setJsonBindPurchase(null);
    jsonBindForm.resetFields();
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["purchases"] }),
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
    ]);
  },
  onError: (error) => message.error(error.message)
});
```

- [ ] **Step 5: Add purchase-scoped import and check mutations**

Add:

```ts
const purchaseImportMutation = useMutation({
  mutationFn: (values: Record<string, unknown>) => {
    if (!sub2apiPurchase) {
      throw new Error("请选择采购批次");
    }
    return createSub2ApiImport({
      instance_id: String(values.instance_id),
      purchase_id: sub2apiPurchase.id,
      select_all: false,
      account_ids: [],
      group_ids: values.group_ids as number[],
      duplicate_policy: values.duplicate_policy as "skip" | "update",
      remark: values.remark ? String(values.remark) : undefined
    });
  },
  onSuccess: async (batch) => {
    message.success(`导入完成：成功 ${batch.success_count}，失败 ${batch.failed_count}，跳过 ${batch.skipped_count}`);
    setSub2apiPurchase(null);
    sub2apiForm.resetFields();
    await queryClient.invalidateQueries({ queryKey: ["accounts"] });
  },
  onError: (error) => message.error(error.message)
});

const purchaseCheckMutation = useMutation({
  mutationFn: (values: Record<string, unknown>) => {
    if (!checkPurchase) {
      throw new Error("请选择采购批次");
    }
    return runAutoSub2ApiAccountCheck({
      instance_id: String(values.instance_id),
      purchase_id: checkPurchase.id,
      include_only_operation: Boolean(values.include_only_operation),
      timeout_seconds: Number(values.timeout_seconds ?? 15),
      remark: values.remark ? String(values.remark) : undefined
    });
  },
  onSuccess: async (batch) => {
    message.success(`检测完成：可用 ${batch.alive_count}，异常 ${batch.abnormal_count}`);
    setCheckPurchase(null);
    checkForm.resetFields();
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["accounts"] }),
      queryClient.invalidateQueries({ queryKey: ["account-check-batches"] })
    ]);
  },
  onError: (error) => message.error(error.message)
});
```

- [ ] **Step 6: Add action buttons for account purchases**

In the operation column after “生成资产”, add:

```tsx
{record.purchase_type === "account" ? (
  <>
    <Button size="small" icon={<UploadOutlined />} onClick={() => setJsonBindPurchase(record)}>
      绑定JSON
    </Button>
    <Button size="small" icon={<CloudUploadOutlined />} onClick={() => setSub2apiPurchase(record)}>
      导入Sub2API
    </Button>
    <Button size="small" icon={<ThunderboltOutlined />} onClick={() => setCheckPurchase(record)}>
      检测
    </Button>
  </>
) : null}
```

- [ ] **Step 7: Add modals**

Add a JSON binding modal with an Ant Design `Upload` controlled through `beforeUpload={(file) => { jsonBindForm.setFieldValue("file", file); return false; }}` and fields `overwrite_existing` and `remark`.

Add a Sub2API import modal with fields `instance_id`, `group_ids`, `duplicate_policy`, and `remark`.

Add a check modal with fields `instance_id`, `include_only_operation`, `timeout_seconds`, and `remark`.

Use existing modal patterns from `AccountsPage.tsx` for `Select` group options and duplicate policy.

- [ ] **Step 8: Run frontend validation**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit if Git metadata is restored**

Run:

```powershell
git status --short
git add frontend/src/api/types.ts frontend/src/api/endpoints.ts frontend/src/pages/PurchasesPage.tsx
git commit -m "feat: add purchase account json workflow"
```

Expected: commit succeeds only after `.git` contains valid repository metadata.

---

### Task 5: End-To-End Verification And Polish

**Files:**
- Modify only files with issues found during verification.
- Evidence: `output/playwright/purchase-account-json-workflow.png`

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: verified purchase workflow and test evidence.

- [ ] **Step 1: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Start local services**

Run backend:

```powershell
cd backend
python -m alembic -c ..\alembic.ini upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected: backend health at `http://127.0.0.1:8000/health`, frontend at `http://127.0.0.1:5173`.

- [ ] **Step 4: Browser verify the workflow**

In the browser:

1. Login with local admin credentials from `README.md`.
2. Open `采购记录`.
3. Create or select an account purchase with quantity `20`.
4. Click `生成资产`; confirm asset status shows 20 generated assets.
5. Click `绑定JSON`; upload `C:\Users\Administrator\Desktop\sub2api-import.json`.
6. Confirm success message reports 20 bound accounts.
7. Open `账号资产`; confirm the purchase assets show email, import batch, and raw credential readiness.
8. Return to `采购记录`; click `导入Sub2API`; select instance and group.
9. Confirm import batch result counts are visible.
10. Click `检测`; confirm account rows show recent HTTP, status, and survival time after check.

- [ ] **Step 5: Save screenshot evidence**

Use Playwright or browser tooling to save:

```text
output/playwright/purchase-account-json-workflow.png
```

Screenshot should show the purchase row with generated assets and action buttons or the account list with bound JSON metadata.

- [ ] **Step 6: Final regression commands**

Run:

```powershell
cd backend
python -m pytest tests/test_purchase_dashboard_features.py tests/test_purchase_account_json_binding.py tests/test_sub2api_import_routes.py tests/test_sub2api_admin_adapter.py -v
```

Run:

```powershell
cd frontend
npm run build
```

Expected: both PASS.

- [ ] **Step 7: Commit verification polish if Git metadata is restored**

Run:

```powershell
git status --short
git add .
git commit -m "test: verify purchase account json workflow"
```

Expected: commit succeeds only after `.git` contains valid repository metadata.
