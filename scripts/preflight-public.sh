#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

failures=0

fail() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

warn() {
  echo "WARN: $1"
}

for path in .env backend/.env backups backend/storage/uploads output frontend/dist backend/.venv frontend/node_modules .agents .superpowers .tmp_sub2api_repo; do
  if [ -e "$path" ]; then
    fail "$path exists locally. Do not publish it to GitHub."
  fi
done

if find . \
  -path './.git' -prune -o \
  -path './.agents' -prune -o \
  -path './.superpowers' -prune -o \
  -path './.tmp_sub2api_repo' -prune -o \
  -path './backend/.venv' -prune -o \
  -path './frontend/node_modules' -prune -o \
  -path './frontend/dist' -prune -o \
  -path './backend/storage/uploads' -prune -o \
  -path './.pytest_cache' -prune -o \
  -path './.playwright-cli' -prune -o \
  \( -name '*.dump' -o -name '*.zip' -o -name '*.sqlite' -o -name '*.db' -o -name '*.log' \) -print | grep -q .; then
  find . \
    -path './.git' -prune -o \
    -path './.agents' -prune -o \
    -path './.superpowers' -prune -o \
    -path './.tmp_sub2api_repo' -prune -o \
    -path './backend/.venv' -prune -o \
    -path './frontend/node_modules' -prune -o \
    -path './frontend/dist' -prune -o \
    -path './backend/storage/uploads' -prune -o \
    -path './.pytest_cache' -prune -o \
    -path './.playwright-cli' -prune -o \
    \( -name '*.dump' -o -name '*.zip' -o -name '*.sqlite' -o -name '*.db' -o -name '*.log' \) -print
  fail "Generated backup/database/log artifacts are present."
fi

if command -v rg >/dev/null 2>&1 && rg --version >/dev/null 2>&1; then
  if rg -n --hidden --glob '!.git/**' --glob '!backend/.venv/**' --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' --glob '!backend/storage/uploads/**' --glob '!scripts/preflight-public.sh' \
    --glob '!.agents/**' --glob '!.superpowers/**' --glob '!.tmp_sub2api_repo/**' \
    '(sk-[A-Za-z0-9_-]{20,}|x-api-key|admin123|password:\s*admin|APP_SECRET_KEY=[A-Za-z0-9_/\+=-]{16,}|APP_FIELD_ENCRYPTION_KEY=[A-Za-z0-9_/\+=-]{16,})' .; then
    fail "Potential secret or default credential string found."
  fi
else
  warn "ripgrep is not installed; secret content scan skipped."
fi

if [ "$failures" -gt 0 ]; then
  echo "Public preflight failed with $failures issue(s)."
  exit 1
fi

echo "Public preflight passed."
