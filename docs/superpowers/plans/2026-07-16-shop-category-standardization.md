# Shop Category Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-maintained standard shop categories and use them for the shop monitor category filter.

**Architecture:** Preserve raw supplier categories on each product, derive standard category metadata during shop synchronization, expose it through the existing shop monitor API, and switch the frontend dropdown/filter to those standard fields.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TypeScript, Ant Design.

## Global Constraints

- Keep raw `category_id` and `category_name` unchanged.
- Auto-merge only names that match after trimming and lowercasing.
- Do not auto-merge semantically similar names.
- Keep changes scoped to shop monitor synchronization and display.

---

### Task 1: Backend Standard Category Metadata

**Files:**
- Modify: `backend/app/services/link_shop_monitor.py`
- Modify: `backend/tests/test_link_shop_monitor.py`

**Interfaces:**
- Produces: product payload keys `standard_category_key`, `standard_category_name`, `category_duplicate_status`.

- [ ] Add failing tests for normalized metadata and duplicate category grouping.
- [ ] Implement normalization helper and batch annotation.
- [ ] Verify focused backend tests pass.

### Task 2: Persistence and API

**Files:**
- Modify: `backend/app/models/shop_monitor.py`
- Modify: `backend/app/schemas/shop_monitor.py`
- Modify: `backend/app/services/shop_monitor_sync.py`
- Create: `backend/alembic/versions/20260716_0002_shop_product_standard_categories.py`

**Interfaces:**
- Consumes: product payload standard category keys from Task 1.
- Produces: API response fields consumed by frontend.

- [ ] Add model and schema fields.
- [ ] Add Alembic migration.
- [ ] Persist standard fields during sync.
- [ ] Verify backend tests pass.

### Task 3: Frontend Filter Uses Standard Category

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/pages/ShopMonitorsPage.tsx`

**Interfaces:**
- Consumes: `standard_category_key` and `standard_category_name` from shop product API response.

- [ ] Extend TypeScript product type.
- [ ] Build category options from standard category fields.
- [ ] Filter products by standard category key.
- [ ] Verify frontend build passes.
