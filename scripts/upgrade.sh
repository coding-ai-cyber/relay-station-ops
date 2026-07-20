#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/backend:${PYTHONPATH:-}"

MODE="${1:-auto}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

backup_native() {
  local output="$BACKUP_DIR/pre-upgrade-$STAMP.zip"
  local python_bin="backend/.venv/bin/python"
  if [ ! -x "$python_bin" ]; then
    python_bin="backend/.venv/Scripts/python.exe"
  fi
  if [ ! -x "$python_bin" ]; then
    echo "Cannot find backend virtualenv Python for backup."
    exit 1
  fi
  "$python_bin" -m app.scripts.export_data --output "$output" --upload-dir "$ROOT_DIR/backend/storage/uploads"
  echo "Backup created: $output"
}

upgrade_native() {
  backup_native
  if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    git pull --ff-only || echo "git pull skipped or failed; continue with current files."
  fi
  ./scripts/install-native.sh
}

upgrade_docker() {
  if docker compose -p relay-station-ops -f docker-compose.prod.yml ps backend >/dev/null 2>&1; then
    local container_backup="/tmp/pre-upgrade-$STAMP.zip"
    docker compose -p relay-station-ops -f docker-compose.prod.yml exec -T backend \
      python -m app.scripts.export_data --output "$container_backup"
    local backend_container
    backend_container="$(docker compose -p relay-station-ops -f docker-compose.prod.yml ps -q backend)"
    docker cp "$backend_container:$container_backup" "$BACKUP_DIR/pre-upgrade-$STAMP.zip"
    echo "Backup created: $BACKUP_DIR/pre-upgrade-$STAMP.zip"
  else
    echo "Docker backend is not running; skip container backup."
  fi

  if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    git pull --ff-only || echo "git pull skipped or failed; continue with current files."
  fi
  docker compose -p relay-station-ops -f docker-compose.prod.yml up -d --build
  docker compose -p relay-station-ops -f docker-compose.prod.yml exec -T backend python -m alembic -c /app/alembic.ini upgrade head
}

upgrade_image() {
  if docker compose -p relay-station-ops -f docker-compose.image.yml ps backend >/dev/null 2>&1; then
    local container_backup="/tmp/pre-upgrade-$STAMP.zip"
    docker compose -p relay-station-ops -f docker-compose.image.yml exec -T backend \
      python -m app.scripts.export_data --output "$container_backup"
    local backend_container
    backend_container="$(docker compose -p relay-station-ops -f docker-compose.image.yml ps -q backend)"
    docker cp "$backend_container:$container_backup" "$BACKUP_DIR/pre-upgrade-$STAMP.zip"
    echo "Backup created: $BACKUP_DIR/pre-upgrade-$STAMP.zip"
  else
    echo "Image backend is not running; skip container backup."
  fi

  if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    git pull --ff-only || echo "git pull skipped or failed; continue with current files."
  fi
  docker compose -p relay-station-ops -f docker-compose.image.yml pull
  docker compose -p relay-station-ops -f docker-compose.image.yml up -d
  docker compose -p relay-station-ops -f docker-compose.image.yml exec -T backend python -m alembic -c /app/alembic.ini upgrade head
}

case "$MODE" in
  native)
    upgrade_native
    ;;
  docker)
    upgrade_docker
    ;;
  image)
    upgrade_image
    ;;
  auto)
    if docker compose -p relay-station-ops -f docker-compose.image.yml ps >/dev/null 2>&1; then
      upgrade_image
    elif docker compose -p relay-station-ops -f docker-compose.prod.yml ps >/dev/null 2>&1; then
      upgrade_docker
    else
      upgrade_native
    fi
    ;;
  *)
    echo "Usage: ./scripts/upgrade.sh [auto|docker|image|native]"
    exit 2
    ;;
esac

echo "Upgrade finished. Verify health endpoint before using the system."
