# Link Shop Store Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add supplier shop monitoring for Link Shop URLs so operators can view current products, prices, stock, and out-of-stock status.

**Architecture:** Store monitored shops and latest product snapshots in PostgreSQL. A backend service calls the public Link Shop endpoints (`/shopApi/Shop/info`, `/categoryList`, `/goodsList`) and upserts snapshots. The frontend adds a dense operations page with manual sync and a 5-minute page-level sync interval.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, React, TanStack Query, Ant Design.

## Global Constraints

- Follow existing backend route/schema/model patterns.
- Use tests before production code for backend parsing and normalization behavior.
- Keep the UI dense and table-driven for repeated operations work.
- Avoid browser scraping; use public backend HTTP requests to reduce WAF issues.

---

### Task 1: Backend Sync Service and Schemas

**Files:**
- Create: `backend/app/services/link_shop_monitor.py`
- Create: `backend/tests/test_link_shop_monitor.py`
- Modify: `backend/app/models/supplier.py`
- Modify: `backend/app/schemas/supplier.py`

**Interfaces:**
- Produces: `parse_link_shop_token(url_or_token: str) -> str`
- Produces: `normalize_link_shop_product(raw: dict, shop_token: str, goods_type: str, category: dict | None) -> dict`

- [ ] Write failing parser and normalization tests.
- [ ] Run `backend\.venv\Scripts\python.exe -m unittest backend.tests.test_link_shop_monitor -v` and verify failure.
- [ ] Implement parser and product normalization.
- [ ] Expose supplier `purchase_url` in schemas.
- [ ] Re-run the test and verify pass.

### Task 2: Persistence and API

**Files:**
- Create: `backend/app/models/shop_monitor.py`
- Create: `backend/app/schemas/shop_monitor.py`
- Create: `backend/app/api/routes/shop_monitors.py`
- Create: `backend/alembic/versions/20260716_0001_shop_monitors.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Produces: `GET /api/shop-monitors`
- Produces: `POST /api/shop-monitors`
- Produces: `POST /api/shop-monitors/import-suppliers`
- Produces: `POST /api/shop-monitors/{monitor_id}/sync`
- Produces: `POST /api/shop-monitors/sync-all`

- [ ] Add persistence models and migration.
- [ ] Add API route using the sync service.
- [ ] Keep generated product rows editable only through sync.
- [ ] Verify backend tests still pass.

### Task 3: Frontend Monitor Page

**Files:**
- Create: `frontend/src/pages/ShopMonitorsPage.tsx`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `frontend/src/RootApp.tsx`
- Modify: `frontend/src/pages/SuppliersPage.tsx`

**Interfaces:**
- Consumes: shop monitor API endpoints from Task 2.
- Produces: `/shop-monitors` route with manual sync, supplier URL import, and 5-minute sync interval.

- [ ] Add TypeScript types and endpoint functions.
- [ ] Add supplier purchase URL field to the supplier form.
- [ ] Build a table-driven monitor page with status tags and sync actions.
- [ ] Add navigation and routing.
- [ ] Run `npm run build`.
