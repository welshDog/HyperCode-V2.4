#!/usr/bin/env bash
set -euo pipefail

SESSION_PATH="SESSION.md"

if [[ -f "$SESSION_PATH" ]]; then
  echo ""
  echo "━━━ LAST SESSION ━━━"
  echo ""
  cat "$SESSION_PATH"
  echo ""
else
  echo ""
  echo "Fresh session — check WHATS_DONE.md"
  echo ""
fi
