# Asset Expiry Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Warn operators before generated assets expire and allow generated assets to receive an expiry date.

**Architecture:** Reuse the existing `GET /api/dashboard/expiring-assets` endpoint for reminder data. Extend purchase asset generation to accept an optional `expired_at`, write it to generated account/server/proxy assets, and add UI affordances in the global header, dashboard risk section, and purchase asset generation flow.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, Ant Design.

## Global Constraints

- Only assets with `expired_at` participate in reminders.
- Preserve existing manual asset editing flows.
- Keep first version as in-app reminders only; no external notification channels.

---

### Task 1: Backend Expiry Propagation

**Files:**
- Modify: `backend/app/schemas/purchase.py`
- Modify: `backend/app/api/routes/purchases.py`
- Modify: `backend/tests/test_purchase_dashboard_features.py`

**Interfaces:**
- Consumes: optional `expired_at` in `POST /api/purchases/{id}/create-assets`.
- Produces: generated `Account`, `Server`, and `ProxyPool` rows with `expired_at`.

### Task 2: Frontend Reminder UI

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/pages/PurchasesPage.tsx`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: existing `getExpiringAssets(7/30)`.
- Produces: top-bar expiry reminder, dashboard expiry list, and create-assets expiry modal.
