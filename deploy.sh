#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

case "$MODE" in
  docker)
    exec "$ROOT_DIR/scripts/install-docker.sh"
    ;;
  image)
    exec "$ROOT_DIR/scripts/install-image.sh"
    ;;
  native)
    exec "$ROOT_DIR/scripts/install-native.sh"
    ;;
  *)
    echo "Usage: ./deploy.sh {docker|image|native}"
    exit 2
    ;;
esac
