#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

random_secret() {
  openssl rand -hex 32
}

require_command docker
require_command openssl
require_command python3

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required."
  exit 1
fi

if [ ! -f .env ]; then
  cat > .env <<EOF
POSTGRES_DB=relay_station_ops
POSTGRES_USER=relay_station_ops
POSTGRES_PASSWORD=$(random_secret)
APP_PORT=${APP_PORT:-8080}
EOF
  echo "Created .env for Docker Compose."
fi

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  python3 - <<'PY'
from pathlib import Path
import secrets

path = Path("backend/.env")
content = path.read_text(encoding="utf-8")
content = content.replace("APP_ENV=local", "APP_ENV=production")
content = content.replace("APP_DEBUG=true", "APP_DEBUG=false")
content = content.replace("APP_SECRET_KEY=", f"APP_SECRET_KEY={secrets.token_urlsafe(48)}")
content = content.replace("APP_FIELD_ENCRYPTION_KEY=", f"APP_FIELD_ENCRYPTION_KEY={secrets.token_urlsafe(48)}")
path.write_text(content, encoding="utf-8")
PY
  echo "Created backend/.env with generated secrets."
fi

docker compose -p relay-station-ops -f docker-compose.prod.yml up -d --build

cat <<'EOF'
Docker deployment started.

Open:
  http://127.0.0.1:8080

Create or reset the first admin account:
  docker compose -p relay-station-ops -f docker-compose.prod.yml exec backend python -m app.scripts.create_admin --username <admin> --password <strong-password> --reset-password
EOF
