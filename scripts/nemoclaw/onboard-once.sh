#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

logs_dir="$root/logs/nemoclaw"
mkdir -p "$logs_dir"

sandbox="${NEMOCLAW_SANDBOX:-broski}"
gateway="${OPENSHELL_GATEWAY:-nemoclaw}"

export PATH="$HOME/.local/bin:$PATH"

bash scripts/nemoclaw/gateway-health.sh >/dev/null

if command -v openshell >/dev/null 2>&1; then
  if openshell sandbox list 2>/dev/null | awk '{print $1}' | grep -qx "$sandbox"; then
    :
  else
    openshell sandbox create --name "$sandbox" --from openclaw >/dev/null
  fi
fi

if ! command -v nemoclaw >/dev/null 2>&1; then
  echo "ERROR: nemoclaw not found on PATH. Run scripts/nemoclaw/install.sh first." >&2
  exit 1
fi

list_out="$(nemoclaw list 2>&1 || true)"
if echo "$list_out" | grep -Eqi "^[[:space:]]*${sandbox}([[:space:]]|\\*|$)"; then
  printf "%s\n" "ok: nemo sandbox registered ($sandbox)"
  exit 0
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
log="$logs_dir/onboard-once-$ts.log"

OPENSHELL_GATEWAY="$gateway" NEMOCLAW_SANDBOX="$sandbox" NEMOCLAW_NONINTERACTIVE=1 NEMOCLAW_FORCE=1 bash scripts/nemoclaw/onboard.sh >"$log" 2>&1 || true

if nemoclaw list 2>/dev/null | grep -Eqi "^[[:space:]]*${sandbox}([[:space:]]|\\*|$)"; then
  printf "%s\n" "ok: nemo sandbox registered ($sandbox)"
  exit 0
fi

tail -n 80 "$log" >&2
echo "ERROR: onboarding did not register sandbox. See $log" >&2
exit 1

