#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_path="$root/.env"
logs_dir="$root/logs/nemoclaw"
mkdir -p "$logs_dir"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
log="$logs_dir/install-$ts.log"
touch "$log"

exec > >(tee "$log") 2>&1

if [ -d "$HOME/.nvm/versions/node" ]; then
  latest="$(ls -1 "$HOME/.nvm/versions/node" | sort -V | tail -n 1)"
  if [ -n "$latest" ]; then
    export PATH="$HOME/.nvm/versions/node/$latest/bin:$PATH"
  fi
fi

read_key_from_env_file() {
  local value
  value="$(grep -E '^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=' "$env_path" | head -n 1 | sed -E 's/^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=[[:space:]]*//')"
  value="$(echo -n "$value" | tr -d '\r' | xargs || true)"
  echo -n "$value"
}

if [ -z "${NVIDIA_API_KEY:-}" ]; then
  if [ ! -f "$env_path" ]; then
    echo "ERROR: NVIDIA_API_KEY not set and .env missing at repo root" >&2
    exit 1
  fi
  export NVIDIA_API_KEY="$(read_key_from_env_file)"
fi

if [ -z "${NVIDIA_API_KEY:-}" ]; then
  echo "ERROR: NVIDIA_API_KEY missing/empty (value not printed)" >&2
  exit 1
fi

echo "info: starting NemoClaw install (log: $log)"

echo "=== NemoClaw install start (UTC $ts) ==="
echo "info: repo_root=$root"
echo "info: NVIDIA_API_KEY present (value not printed)"
echo

curl -fsSL https://nvidia.com/nemoclaw.sh | bash

echo
echo "=== Post-install checks ==="
command -v nemoclaw
nemoclaw help | sed -n '1,20p'
echo "=== NemoClaw install end ==="

if grep -n -E '^[[:space:]]*(\\[ERROR\\]|ERROR:)' "$log" >/dev/null; then
  echo "FAIL: install log contains ERROR-level lines (see $log)" >&2
  exit 1
fi

echo "ok: NemoClaw install completed (see $log)"
