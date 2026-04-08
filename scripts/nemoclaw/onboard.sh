#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

env_path="$root/.env"
logs_dir="$root/logs/nemoclaw"
mkdir -p "$logs_dir"

sandbox="${NEMOCLAW_SANDBOX:-broski}"

export PATH="$HOME/.local/bin:$PATH"

if [ -d "$HOME/.nvm/versions/node" ]; then
  latest="$(ls -1 "$HOME/.nvm/versions/node" | sort -V | tail -n 1)"
  if [ -n "$latest" ]; then
    export PATH="$HOME/.nvm/versions/node/$latest/bin:$PATH"
  fi
fi

runs_log="$logs_dir/onboard-runs.log"
touch "$runs_log"
now="$(date -u +%s)"
tmp="$runs_log.tmp"
awk -v now="$now" '($1+0) > (now-21600) { print $1 }' "$runs_log" > "$tmp" 2>/dev/null || true
mv -f "$tmp" "$runs_log"
echo "$now" >> "$runs_log"
recent="$(awk -v now="$now" '($1+0) > (now-3600) { c++ } END { print c+0 }' "$runs_log" 2>/dev/null || echo 0)"
if [ "${recent:-0}" -gt 3 ] && [ "${NEMOCLAW_FORCE:-}" != "1" ]; then
  echo "ERROR: Too many onboarding attempts in the last hour ($recent). Fix root cause first (run scripts/nemoclaw/diagnose.sh)." >&2
  exit 2
fi

lock_dir="$logs_dir/onboard.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "ERROR: NemoClaw onboarding already running (lock: $lock_dir)" >&2
  exit 2
fi
cleanup() { rmdir "$lock_dir" 2>/dev/null || true; }
trap cleanup EXIT

if [ ! -f "$env_path" ]; then
  echo "ERROR: Missing .env at repo root" >&2
  exit 1
fi

key="$(grep -E '^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=' "$env_path" | head -n 1 | sed -E 's/^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=[[:space:]]*//')"
key="$(echo -n "$key" | tr -d '\r' | xargs || true)"
if [ -z "${key}" ]; then
  echo "ERROR: NVIDIA_API_KEY missing/empty in .env (value not printed)" >&2
  exit 1
fi

export NVIDIA_API_KEY="$key"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
log="$logs_dir/onboard-$ts.log"

printf "%s\n" "info: onboarding NemoClaw sandbox '$sandbox' (log: $log)"

if ! command -v nemoclaw >/dev/null 2>&1; then
  echo "ERROR: nemoclaw not found on PATH. Run scripts/nemoclaw/install.sh first." >&2
  exit 1
fi

for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if docker ps >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! docker ps >/dev/null 2>&1; then
  echo "ERROR: Docker not reachable from WSL. Ensure Docker Desktop is running and WSL integration is enabled for Ubuntu-22.04." >&2
  exit 1
fi

if docker ps --filter "name=^openshell-cluster-nemoclaw$" --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -qE 'openshell-cluster-nemoclaw.*8080->'; then
  if [ "${NEMOCLAW_REUSE_GATEWAY:-}" != "1" ]; then
    printf "%s\n" "info: freeing port 8080 by removing existing openshell-cluster-nemoclaw container"
    docker rm -f openshell-cluster-nemoclaw >/dev/null 2>&1 || true
    sleep 2
  fi
fi

list_out="$(nemoclaw list 2>&1 || true)"
if echo "$list_out" | grep -Eqi "^[[:space:]]*${sandbox}([[:space:]]|\\*|$)"; then
  printf "%s\n" "ok: sandbox already registered ($sandbox)"
  exit 0
fi

if [ "${NEMOCLAW_NONINTERACTIVE:-}" = "1" ]; then
  printf "%s\n" "info: running non-interactive onboarding (sandbox: $sandbox)"
  printf "%b" "$sandbox\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n" | nemoclaw onboard >"$log" 2>&1
else
  printf "%s\n" "info: run will be interactive. When prompted for sandbox name, enter: $sandbox"
  if command -v script >/dev/null 2>&1; then
    script -q -f "$log" -c "nemoclaw onboard"
  else
    nemoclaw onboard >"$log" 2>&1
  fi
fi

tail -n 30 "$log"
