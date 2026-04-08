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

if [ ! -f "$env_path" ]; then
  echo "Missing .env at repo root" >&2
  exit 1
fi

value="$(grep -E '^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=' "$env_path" | head -n 1 | sed -E 's/^[[:space:]]*NVIDIA_API_KEY[[:space:]]*=[[:space:]]*//')"
value="$(echo -n "$value" | tr -d '\r' | xargs || true)"
if [ -z "${value}" ]; then
  echo "NVIDIA_API_KEY missing or empty in .env" >&2
  exit 1
fi

export NVIDIA_API_KEY="$value"

command -v openshell >/dev/null
command -v openclaw >/dev/null
command -v nemoclaw >/dev/null

nemoclaw "$sandbox" status >/dev/null
openshell inference set --provider nvidia-nim --model nvidia/nemotron-3-super-120b-a12b >/dev/null
openclaw agent --agent main --local -m "ping" --session-id keycheck >/dev/null

echo "ok: NVIDIA_API_KEY works for NVIDIA cloud inference (value not printed)"
echo "keycheck OK"
