# Sub2API Revenue Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let revenue management manually and automatically sync paid revenue records from active Sub2API instances.

**Architecture:** Add a backend adapter that probes common Sub2API revenue/order endpoints, normalizes remote records into local `Revenue` rows, and upserts by instance/order identity. Expose a finance/admin-only sync endpoint and wire the revenue page to call it. Reuse the existing scheduler pattern for optional periodic syncing.

**Tech Stack:** FastAPI, SQLAlchemy, httpx, React, TypeScript, TanStack Query.

## Global Constraints

- Keep manual revenue CRUD unchanged.
- Do not create duplicate revenue rows for the same Sub2API instance and remote order.
- Treat unknown remote schemas defensively and import only records with a usable amount and order id.
- Start with recharge/order/payment income only; do not implement model-consumption revenue allocation in this pass.

---

### Task 1: Normalize and Upsert Remote Revenue

**Files:**
- Create: `backend/app/services/sub2api_revenue_sync.py`
- Create: `backend/tests/test_sub2api_revenue_sync.py`
- Modify: `backend/app/schemas/revenue.py`

**Interfaces:**
- Produces: `Sub2APIRevenueSyncResult`, `sync_sub2api_revenues(db, instance=None)`.

- [ ] Add tests for remote payload normalization.
- [ ] Add tests for create-vs-update by `related_order_no`.
- [ ] Implement the service.

### Task 2: API and Scheduler

**Files:**
- Modify: `backend/app/api/routes/revenues.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/revenue_sync_scheduler.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `sync_sub2api_revenues`.
- Produces: `POST /api/revenues/sync-sub2api`.

- [ ] Add a route returning sync summary.
- [ ] Add opt-in scheduler settings and startup hook.
- [ ] Keep manual sync available regardless of scheduler setting.

### Task 3: Frontend Sync Button

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/pages/RevenuesPage.tsx`

**Interfaces:**
- Consumes: `Sub2APIRevenueSyncResult`.

- [ ] Add endpoint and type.
- [ ] Add "同步 Sub2API" button.
- [ ] Refresh revenue list after sync.
