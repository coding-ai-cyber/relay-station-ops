# Backend

FastAPI backend for Sub2API Ops.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set unique values for:

```text
APP_SECRET_KEY
APP_FIELD_ENCRYPTION_KEY
DATABASE_URL
```

Run migrations from the repository root:

```bash
python -m alembic -c alembic.ini upgrade head
```

Create an administrator:

```bash
cd backend
python -m app.scripts.create_admin --username <admin-user> --password <strong-password> --reset-password
```

Start:

```bash
python -m uvicorn app.main:app --reload
```

## Data Portability

Export:

```bash
python -m app.scripts.export_data --output ../backups/backup.zip
```

Import:

```bash
python -m app.scripts.import_data --input ../backups/backup.zip
```

The import command checks `APP_FIELD_ENCRYPTION_KEY` fingerprint by default.
