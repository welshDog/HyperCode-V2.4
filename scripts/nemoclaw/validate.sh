#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_path="$root/.env"
sandbox="${NEMOCLAW_SANDBOX:-broski}"

if [ -d "$HOME/.nvm/versions/node" ]; then
  latest="$(ls -1 "$HOME/.nvm/versions/node" | sort -V | tail -n 1)"
  if [ -n "$latest" ]; then
    export PATH="$HOME/.nvm/versions/node/$latest/bin:$PATH"
  fi
fi

command -v nemoclaw >/dev/null
echo "PASS: nemoclaw on PATH"
command -v openclaw >/dev/null
echo "PASS: openclaw on PATH"

list_out="$(nemoclaw list 2>&1 || true)"
if echo "$list_out" | grep -qi "No sandboxes registered"; then
  echo "FAIL: No NemoClaw sandboxes registered. Run: NEMOCLAW_SANDBOX='$sandbox' bash scripts/nemoclaw/onboard.sh" >&2
  echo "Tip: If onboarding fails repeatedly, run: bash scripts/nemoclaw/diagnose.sh" >&2
  exit 1
fi
if ! echo "$list_out" | grep -Eqi "^[[:space:]]*${sandbox}([[:space:]]|\\*|$)"; then
  echo "FAIL: NemoClaw sandbox '$sandbox' not registered. Run: NEMOCLAW_SANDBOX='$sandbox' bash scripts/nemoclaw/onboard.sh" >&2
  echo "Tip: If onboarding fails repeatedly, run: bash scripts/nemoclaw/diagnose.sh" >&2
  exit 1
fi
echo "PASS: NemoClaw sandbox registered ($sandbox)"

if [ -z "${NVIDIA_API_KEY:-}" ]; then
  if [ -f "$env_path" ]; then
    value="$(grep -E '^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=' "$env_path" | head -n 1 | sed -E 's/^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=[[:space:]]*//')"
    value="$(echo -n "$value" | tr -d '\r' | xargs || true)"
    if [ -n "$value" ]; then
      export NVIDIA_API_KEY="$value"
    fi
  fi
fi

if [ -n "${NVIDIA_API_KEY:-}" ]; then
  echo "PASS: NVIDIA_API_KEY present (value not printed)"
else
  echo "WARN: NVIDIA_API_KEY not detected in environment"
fi

echo "PASS: validate.sh complete"
