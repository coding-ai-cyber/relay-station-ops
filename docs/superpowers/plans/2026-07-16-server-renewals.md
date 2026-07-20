# Server Renewal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renew an existing server asset by creating a new purchase/cost record and extending the server expiry date.

**Architecture:** Add a server renewal request schema and route. The route creates a new `Purchase` of type `server`, creates its generated `CostItem`, updates the target server's `expired_at`, and keeps the server asset as a single continuing asset.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, Ant Design.

## Global Constraints

- Do not mutate the original purchase record.
- Do not create a duplicate server asset.
- Renewal creates a new purchase and generated cost item.
- Server `expired_at` becomes the selected renewal expiry date.

---

### Task 1: Backend Server Renewal

**Files:**
- Modify: `backend/app/schemas/server.py`
- Modify: `backend/app/api/routes/servers.py`
- Create: `backend/tests/test_server_renewals.py`

**Interfaces:**
- Produces: `POST /api/servers/{server_id}/renew`.
- Returns: `PurchaseRead` for the renewal purchase.

### Task 2: Frontend Renewal Flow

**Files:**
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/pages/ServersPage.tsx`

**Interfaces:**
- Adds a "续费" button per server row.
- Collects renewal amount, currency, new expiry date, payment method, purchase date, cost flags, and remark.
