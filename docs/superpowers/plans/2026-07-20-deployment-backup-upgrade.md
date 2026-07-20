# Deployment Backup Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public-GitHub-safe deployment, full business data backup/restore, and upgrade scripts for Docker and non-Docker installations.

**Architecture:** Keep runtime deployment in shell scripts and Docker Compose files. Keep business data export/import in backend Python management modules that package a PostgreSQL dump plus uploaded files into one zip. Keep release hygiene in a preflight script that scans for secrets and local data before publishing.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, pg_dump/pg_restore, Docker Compose, Vite/React, Bash.

## Global Constraints

- Do not commit `.env`, database dumps, uploads, logs, or generated frontend/backend artifacts.
- Exclude audit logs from exported business backups.
- Preserve `APP_FIELD_ENCRYPTION_KEY` across machines so encrypted credentials remain decryptable.
- Docker deployment is the recommended production path; native deployment remains supported.
- Scripts must be safe to re-run and must fail clearly when required tools are missing.

---

### Task 1: Backup Archive Core

**Files:**
- Create: `backend/app/services/data_portability.py`
- Create: `backend/app/scripts/export_data.py`
- Create: `backend/app/scripts/import_data.py`
- Test: `backend/tests/test_data_portability.py`

**Interfaces:**
- Produces: `export_backup(output_path: Path, database_url: str, upload_dir: Path, app_field_encryption_key: str) -> Path`
- Produces: `import_backup(input_path: Path, database_url: str, upload_dir: Path, app_field_encryption_key: str, force: bool = False) -> None`
- Produces: CLI modules `python -m app.scripts.export_data --output backup.zip` and `python -m app.scripts.import_data --input backup.zip`

- [ ] Write tests that patch subprocess and assert `pg_dump` excludes `audit_logs`, backup metadata contains the encryption key fingerprint, uploads are zipped, and import refuses mismatched keys unless `--force` is used.
- [ ] Run `pytest backend/tests/test_data_portability.py -q` and confirm it fails because the module does not exist.
- [ ] Implement the service and CLI wrappers.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Deployment Scripts And Compose

**Files:**
- Create: `deploy.sh`
- Create: `scripts/install-docker.sh`
- Create: `scripts/install-native.sh`
- Create: `scripts/upgrade.sh`
- Create: `scripts/preflight-public.sh`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.prod.yml`
- Modify: `.gitignore`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces: `./deploy.sh docker`, `./deploy.sh native`, `./scripts/upgrade.sh`, `./scripts/preflight-public.sh`

- [ ] Add shell script smoke tests or syntax verification via `bash -n`.
- [ ] Implement Docker Compose production stack with Postgres volume, uploads volume, backend API, and frontend Nginx.
- [ ] Implement native installer that creates backend venv, installs npm dependencies, runs Alembic, and optionally creates admin.
- [ ] Implement upgrade script that creates a backup before pulling/upgrading, then runs migrations/build/restart guidance.
- [ ] Implement preflight scanner for secrets and local data.

### Task 3: Public Documentation And Default Cleanup

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/src/pages/LoginPage.tsx`

**Interfaces:**
- Produces: public-safe docs with no real credentials or default login prefill.

- [ ] Remove login form default credentials.
- [ ] Replace default password docs with explicit “create your own admin password”.
- [ ] Document Docker deploy, native deploy, export, import, upgrade, and GitHub preflight.
- [ ] Run frontend build and backend tests.
