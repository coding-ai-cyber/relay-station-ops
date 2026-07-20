# Account Supplier Shop Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let account suppliers use one login/shop address, opt into shop monitoring, and collect products from both Link Shop and CatFK/Yunmao stores.

**Architecture:** Extend the current Link Shop monitor into a host-aware shop monitor client that parses supported shop URLs into `(platform, token)` and selects the correct base URL for sync. Store supplier monitoring intent on `suppliers.monitor_shop`, and import monitors from opted-in account suppliers using `login_url`. Keep the existing product snapshot tables and frontend monitor workflow.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, unittest, React, TanStack Query, Ant Design, TypeScript.

## Global Constraints

- Keep existing supplier and shop monitor API shapes backward compatible where possible.
- Use `login_url` as the single account supplier shop address edited by the UI.
- Do not import suppliers into monitoring unless `monitor_shop` is true, supplier type is `account`, and `login_url` is a supported shop URL.
- Support `https://pay.ldxp.cn/shop/{token}` and `https://catfk.com/shop/{token}`.
- Identify monitors by `(platform, shop_token)`.
- Preserve the existing table-driven operations UI.

---

## File Structure

- `backend/app/services/link_shop_monitor.py`: parse supported shop URLs, normalize products, and fetch products from the correct platform base URL.
- `backend/app/services/shop_monitor_sync.py`: pass monitor platform into the client during sync.
- `backend/app/api/routes/shop_monitors.py`: create/import monitors with parsed platform and token.
- `backend/app/models/supplier.py`: add `monitor_shop`.
- `backend/app/schemas/supplier.py`: expose `monitor_shop` for create/update/read.
- `backend/app/models/shop_monitor.py`: change uniqueness from global token to `(platform, shop_token)`.
- `backend/alembic/versions/20260716_0002_supplier_monitor_shop_multiplatform.py`: add `monitor_shop` and migrate monitor uniqueness.
- `backend/tests/test_link_shop_monitor.py`: add parser and CatFK normalization tests.
- `backend/tests/test_shop_monitor_import.py`: add focused import tests for opted-in login URLs.
- `frontend/src/api/types.ts`: expose supplier `monitor_shop`.
- `frontend/src/pages/SuppliersPage.tsx`: collapse account supplier URLs and add the monitoring switch.
- `frontend/src/pages/ShopMonitorsPage.tsx`: update copy, placeholders, labels, and item link generation by platform.

### Task 1: Backend Platform Parser and Client

**Files:**
- Modify: `backend/app/services/link_shop_monitor.py`
- Modify: `backend/tests/test_link_shop_monitor.py`

**Interfaces:**
- Produces: `ShopPlatformConfig(platform: str, host: str, base_url: str)`
- Produces: `parse_shop_reference(url_or_token: str) -> tuple[ShopPlatformConfig, str]`
- Keeps: `parse_link_shop_token(url_or_token: str) -> str`
- Updates: `LinkShopClient(platform: str = "link_shop", timeout: float = 20.0)`

- [ ] Add failing tests for CatFK URL parsing, unsupported hosts, and CatFK product normalization.
- [ ] Run `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_link_shop_monitor -v` and verify the new CatFK parser test fails.
- [ ] Implement `parse_shop_reference` and platform-aware `LinkShopClient`.
- [ ] Re-run `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_link_shop_monitor -v` and verify pass.

### Task 2: Supplier Monitor Flag and Monitor Import

**Files:**
- Modify: `backend/app/models/supplier.py`
- Modify: `backend/app/schemas/supplier.py`
- Modify: `backend/app/models/shop_monitor.py`
- Modify: `backend/app/api/routes/shop_monitors.py`
- Modify: `backend/app/services/shop_monitor_sync.py`
- Create: `backend/tests/test_shop_monitor_import.py`
- Create: `backend/alembic/versions/20260716_0002_supplier_monitor_shop_multiplatform.py`

**Interfaces:**
- Consumes: `parse_shop_reference(url_or_token: str) -> tuple[ShopPlatformConfig, str]`
- Produces: `Supplier.monitor_shop: bool`
- Produces: monitor import from account supplier `login_url`

- [ ] Write failing import tests showing only opted-in account suppliers with supported `login_url` are imported.
- [ ] Run `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_shop_monitor_import -v` and verify failure.
- [ ] Add `monitor_shop` to supplier model and schemas.
- [ ] Update monitor uniqueness and API create/import logic to store `(platform, shop_token)`.
- [ ] Add Alembic migration for `suppliers.monitor_shop` and monitor uniqueness.
- [ ] Re-run `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_shop_monitor_import backend.tests.test_link_shop_monitor -v` and verify pass.

### Task 3: Frontend Supplier and Monitor UX

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/pages/SuppliersPage.tsx`
- Modify: `frontend/src/pages/ShopMonitorsPage.tsx`

**Interfaces:**
- Consumes: `Supplier.monitor_shop`
- Produces: account supplier form with one `login_url` field and an opt-in monitor switch.

- [ ] Add `monitor_shop?: boolean` to the frontend supplier type.
- [ ] Update supplier form to remove `purchase_url` editing and show the monitoring switch for account suppliers.
- [ ] Update supplier table/search labels to use login/shop address.
- [ ] Update shop monitor copy and placeholder to accept Link Shop or CatFK URLs.
- [ ] Generate item links using monitor platform instead of always `pay.ldxp.cn`.
- [ ] Run `npm run build` from `frontend` and verify pass.

### Task 4: Final Verification

**Files:**
- Verify all touched backend/frontend files.

**Interfaces:**
- Confirms the whole workflow is working after all tasks.

- [ ] Run backend focused tests: `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_link_shop_monitor backend.tests.test_shop_monitor_import backend.tests.test_shop_monitor_scheduler -v`.
- [ ] Run frontend build: `npm run build` from `frontend`.
- [ ] Check generated migration and UI strings for consistency.
