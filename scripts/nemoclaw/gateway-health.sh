#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

logs_dir="$root/logs/nemoclaw"
mkdir -p "$logs_dir"

gateway="${OPENSHELL_GATEWAY:-nemoclaw}"
port="${OPENSHELL_GATEWAY_PORT:-8080}"
container="${OPENSHELL_GATEWAY_CONTAINER:-openshell-cluster-nemoclaw}"

export PATH="$HOME/.local/bin:$PATH"

if ! command -v openshell >/dev/null 2>&1; then
  echo "ERROR: openshell not found on PATH. Run scripts/nemoclaw/install.sh first." >&2
  exit 1
fi

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if docker ps >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! docker ps >/dev/null 2>&1; then
  echo "ERROR: Docker not reachable from WSL." >&2
  exit 1
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
log="$logs_dir/gateway-health-$ts.log"

if docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
  state="$(docker inspect "$container" --format '{{.State.Status}}' 2>/dev/null || true)"
  health="$(docker inspect "$container" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)"

  if [ "$state" != "running" ]; then
    docker start "$container" >/dev/null
  fi

  if [ -n "$health" ] && [ "$health" != "healthy" ]; then
    docker restart "$container" >/dev/null
  fi
else
  OPENSHELL_GATEWAY="$gateway" openshell gateway start --name "$gateway" --port "$port" >>"$log" 2>&1
fi

ok=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if OPENSHELL_GATEWAY="$gateway" openshell status >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" != "1" ]; then
  OPENSHELL_GATEWAY="$gateway" openshell status >>"$log" 2>&1 || true
  echo "ERROR: gateway not reachable (see $log)" >&2
  exit 1
fi

OPENSHELL_GATEWAY="$gateway" openshell status | tee -a "$log"
