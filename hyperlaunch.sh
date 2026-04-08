#!/usr/bin/env bash
# =============================================================================
# 🚀 HyperLaunch — One-Command HyperCode V2.0 Startup
# =============================================================================
# Usage:
#   ./hyperlaunch.sh              # Full launch
#   ./hyperlaunch.sh --dry-run    # Pre-flight checks only
#   ./hyperlaunch.sh --status     # Live system status
#   ./hyperlaunch.sh --teardown   # Graceful shutdown
#   ./hyperlaunch.sh --watchdog   # Launch + stay watching
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colour helpers ────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${CYAN}[HyperLaunch]${NC} $*"; }
ok()   { echo -e "${GREEN}✅${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️ ${NC} $*"; }
fail() { echo -e "${RED}❌${NC} $*"; }

echo
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  🚀 HyperCode V2.0 — HyperLaunch            ║${NC}"
echo -e "${BOLD}${CYAN}║  Unified System Initialization Commander     ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo

# ── Python check ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  fail "Python not found. Install Python 3.10+"
  exit 1
fi

PYTHON="python3"
command -v python3 &>/dev/null || PYTHON="python"

# ── Optional: install rich for pretty output ──────────────────────────────────
if ! $PYTHON -c "import rich" &>/dev/null 2>&1; then
  warn "'rich' not installed — output will be plain text."
  warn "Install for colours: pip install rich"
fi

# ── Load .env if present ──────────────────────────────────────────────────────
if [ -f ".env" ]; then
  log "Loading .env..."
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  ok ".env loaded"
else
  warn ".env not found — using existing environment"
fi

# ── Forward all args to hyperlaunch.py ───────────────────────────────────────
log "Launching HyperCode V2.0..."
echo

exec $PYTHON "$SCRIPT_DIR/hyperlaunch.py" "$@"
