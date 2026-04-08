#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_path="$root/.env"

test -f "$env_path"

value="$(grep -E '^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=' "$env_path" | head -n 1 | sed -E 's/^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=[[:space:]]*//')"
value="$(echo -n "$value" | tr -d '\r' | xargs || true)"

if [ -z "${value}" ]; then
  echo "NVIDIA_API_KEY missing or empty in .env" >&2
  exit 1
fi

echo "ok: NVIDIA_API_KEY present in .env (value not printed)"

