#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/backend:${PYTHONPATH:-}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_command python3
require_command npm

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  python3 - <<'PY'
from pathlib import Path
import secrets

path = Path("backend/.env")
content = path.read_text(encoding="utf-8")
content = content.replace("APP_SECRET_KEY=", f"APP_SECRET_KEY={secrets.token_urlsafe(48)}")
content = content.replace("APP_FIELD_ENCRYPTION_KEY=", f"APP_FIELD_ENCRYPTION_KEY={secrets.token_urlsafe(48)}")
path.write_text(content, encoding="utf-8")
PY
  echo "Created backend/.env. Review DATABASE_URL before continuing if PostgreSQL is not local."
fi

if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi

if [ -x backend/.venv/bin/python ]; then
  PYTHON_BIN="backend/.venv/bin/python"
else
  PYTHON_BIN="backend/.venv/Scripts/python.exe"
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r backend/requirements.txt
"$PYTHON_BIN" -m alembic -c alembic.ini upgrade head

if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
  "$PYTHON_BIN" -m app.scripts.create_admin \
    --username "$ADMIN_USERNAME" \
    --password "$ADMIN_PASSWORD" \
    --reset-password
else
  echo "Skip admin creation. Set ADMIN_USERNAME and ADMIN_PASSWORD to create one automatically."
fi

cd frontend
npm ci
npm run build
cd "$ROOT_DIR"

cat <<EOF
Native deployment prepared.

Start backend:
  cd backend
  ../$PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Serve frontend/dist with Nginx or another static file server, proxying /api to the backend.
EOF
