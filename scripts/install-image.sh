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
BACKEND_IMAGE=ghcr.io/coding-ai-cyber/relay-station-ops-backend:latest
FRONTEND_IMAGE=ghcr.io/coding-ai-cyber/relay-station-ops-frontend:latest
EOF
  echo "Created .env for image deployment."
fi

if [ ! -f backend/.env ]; then
  cat > backend/.env <<EOF
APP_NAME=Relay Station Ops
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=$(random_secret)
APP_FIELD_ENCRYPTION_KEY=$(random_secret)
DATABASE_URL=postgresql+psycopg://relay_station_ops:relay_station_ops@localhost:5432/relay_station_ops
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FILE_STORAGE_DIR=storage/uploads
SHOP_MONITOR_AUTO_SYNC_ENABLED=true
SHOP_MONITOR_SYNC_INTERVAL_SECONDS=300
SHOP_MONITOR_SUCCESS_INTERVAL_SECONDS=3600
SHOP_MONITOR_FAILURE_COOLDOWN_SECONDS=3600
SHOP_MONITOR_MAX_PER_BATCH=1
SUB2API_REVENUE_AUTO_SYNC_ENABLED=false
SUB2API_REVENUE_SYNC_INTERVAL_SECONDS=600
SUB2API_ACCOUNT_CHECK_AUTO_ENABLED=true
SUB2API_ACCOUNT_CHECK_INTERVAL_SECONDS=600
SUB2API_ACCOUNT_CHECK_ONLY_OPERATION=false
EOF
  echo "Created backend/.env with generated secrets."
fi

docker compose -p relay-station-ops -f docker-compose.image.yml pull
docker compose -p relay-station-ops -f docker-compose.image.yml up -d

cat <<'EOF'
Image deployment started.

Open:
  http://127.0.0.1:8080

Create or reset the first admin account:
  docker compose -p relay-station-ops -f docker-compose.image.yml exec backend python -m app.scripts.create_admin --username <admin> --password <strong-password> --reset-password
EOF
