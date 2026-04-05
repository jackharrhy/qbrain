#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "Loaded qbrain env from $ENV_FILE"
else
  echo "No .env found at $ENV_FILE"
fi
