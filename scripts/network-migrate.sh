#!/usr/bin/env bash
# ── Phase 10B: Network Migration Helper ───────────────────────────────────────
# Safely recreates the Docker Compose network topology after Phase 10B changes.
# Old topology: single flat backend-net (external + public)
# New topology:  5 purpose-specific networks (2 internet-accessible, 3 internal)
#
# Usage:
#   ./scripts/network-migrate.sh [--dry-run]
#
# The script:
#   1. Stops all running Compose services
#   2. Removes old external networks that no longer exist in compose
#   3. Brings the stack back up (creates new networks automatically)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🔍 DRY RUN — no changes will be made"
fi

run() {
  if $DRY_RUN; then
    echo "  [dry-run] $*"
  else
    "$@"
  fi
}

cd "$COMPOSE_ROOT"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Phase 10B — Docker Compose Network Migration"
echo "════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Show current network state ────────────────────────────────────────
echo "▶ Current Docker networks:"
docker network ls --filter name=hypercode --format "  {{.Name}} ({{.Driver}})"
echo ""

# ── Step 2: Bring down the full stack (all profiles) ──────────────────────────
echo "▶ Stopping all Compose services..."
run docker compose \
  --profile agents --profile hyper --profile health \
  --profile discord --profile mission --profile ops \
  down --remove-orphans
echo ""

# ── Step 3: Remove stale external networks from old topology ──────────────────
# These were the old external networks that are no longer defined in compose.
OLD_NETS=(
  "hypercode_public_net"   # old backend-net name
  "hypercode-agents-net"   # old agents external net
)

for net in "${OLD_NETS[@]}"; do
  if docker network ls --format "{{.Name}}" | grep -qx "$net"; then
    echo "▶ Removing stale network: $net"
    run docker network rm "$net" || echo "  ⚠ Could not remove $net (may still have connected containers)"
  else
    echo "  ✓ Network not found (already gone): $net"
  fi
done
echo ""

# ── Step 4: Bring up core stack (creates new networks) ────────────────────────
echo "▶ Starting core stack (creates new networks)..."
run docker compose up -d
echo ""

# ── Step 5: Verify new networks ───────────────────────────────────────────────
if ! $DRY_RUN; then
  echo "▶ New network state:"
  docker network ls --filter name=hypercode --format "  {{.Name}} ({{.Driver}})" | sort
  echo ""

  echo "▶ Network isolation check:"
  for net in hypercode_data_net hypercode_obs_net; do
    internal=$(docker network inspect "$net" --format "{{.Internal}}" 2>/dev/null || echo "not found")
    if [[ "$internal" == "true" ]]; then
      echo "  ✅ $net — internal=true (no internet gateway)"
    elif [[ "$internal" == "false" ]]; then
      echo "  ⚠  $net — internal=false (has internet access — check config!)"
    else
      echo "  ❓ $net — $internal"
    fi
  done
  echo ""
fi

echo "════════════════════════════════════════════════════════"
echo "  Migration complete!"
echo ""
echo "  Next steps:"
echo "    docker compose --profile agents up -d   # start agents"
echo "    docker compose --profile hyper up -d    # start hyper agents"
echo "    docker compose --profile health up -d   # start health stack"
echo "════════════════════════════════════════════════════════"
echo ""
