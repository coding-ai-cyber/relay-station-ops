# Web Maintenance Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Web system maintenance page for version visibility, backup export/download, backup import, and upgrade guidance.

**Architecture:** Add admin-only FastAPI endpoints under `/api/system-maintenance`. Reuse the existing `data_portability` service for export/import. Add a React page under the system menu using Ant Design cards, upload controls, and operational command snippets.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL backup zip, React, Ant Design, TanStack Query.

## Global Constraints

- Only admin users can export/import backups or view maintenance metadata.
- Import rejects mismatched `APP_FIELD_ENCRYPTION_KEY` unless force is explicitly requested.
- Web page must not directly run `git pull`, rebuild, or restart the server in this iteration.
- Backups must be written outside `backend/storage/uploads`.

---

### Task 1: Backend Maintenance API

**Files:**
- Create: `backend/app/api/routes/system_maintenance.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_system_maintenance.py`

**Interfaces:**
- Produces: `GET /api/system-maintenance/status`
- Produces: `POST /api/system-maintenance/backups`
- Produces: `GET /api/system-maintenance/backups/{filename}/download`
- Produces: `POST /api/system-maintenance/import`

- [ ] Write route tests for admin-only registration and backup/import calling the portability service.
- [ ] Implement the routes.
- [ ] Run focused backend tests.

### Task 2: Frontend Maintenance Page

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Create: `frontend/src/pages/SystemMaintenancePage.tsx`
- Modify: `frontend/src/RootApp.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

**Interfaces:**
- Produces: `/system-maintenance` route.
- Produces: menu item `系统维护`.

- [ ] Add types and endpoint wrappers.
- [ ] Add page with status cards, backup export/download, backup upload/import, and upgrade commands.
- [ ] Add route and menu entry.
- [ ] Run frontend build.
