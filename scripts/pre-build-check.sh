#!/bin/bash
# ============================================================
# HyperCode Pre-Build Disk + Memory Safety Check
# Run this before any docker build to prevent OOM/OOD crashes
# Agent X should call this before spinning up new builds
# ============================================================

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

MIN_DISK_GB=${MIN_DISK_GB:-15}
WARN_DISK_GB=${WARN_DISK_GB:-25}
MIN_MEM_MB=${MIN_MEM_MB:-1024}

echo ""
echo -e "${BOLD}⚡ HyperCode Pre-Build Safety Check${NC}"
echo "======================================="

# ── Disk Check ──────────────────────────────────────────────
AVAILABLE_KB=$(df / | awk 'NR==2 {print $4}')
AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))

echo -e "💾 Disk available: ${BOLD}${AVAILABLE_GB}GB${NC}"

if [ "$AVAILABLE_GB" -lt "$MIN_DISK_GB" ]; then
  echo -e "${RED}❌ ABORT: Less than ${MIN_DISK_GB}GB free (${AVAILABLE_GB}GB available)${NC}"
  echo -e "${YELLOW}   Run: docker system prune -f && docker builder prune -f --keep-storage=5gb${NC}"
  exit 1
elif [ "$AVAILABLE_GB" -lt "$WARN_DISK_GB" ]; then
  echo -e "${YELLOW}⚠️  WARNING: Only ${AVAILABLE_GB}GB free — consider pruning before building${NC}"
  echo -e "${YELLOW}   Run: docker image prune -f --filter until=48h${NC}"
else
  echo -e "${GREEN}✅ Disk OK${NC}"
fi

# ── Docker Disk Check ────────────────────────────────────────
echo ""
echo "🐳 Docker disk usage:"
docker system df --format "   {{.Type}}: {{.Size}} (reclaimable: {{.Reclaimable}})" 2>/dev/null || echo "   (docker system df unavailable)"

# ── Memory Check ────────────────────────────────────────────
FREE_MEM_MB=$(awk '/MemAvailable/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo "0")

echo ""
if [ "$FREE_MEM_MB" -gt 0 ]; then
  echo -e "🧠 Memory available: ${BOLD}${FREE_MEM_MB}MB${NC}"
  if [ "$FREE_MEM_MB" -lt "$MIN_MEM_MB" ]; then
    echo -e "${RED}❌ ABORT: Less than ${MIN_MEM_MB}MB RAM free (${FREE_MEM_MB}MB available)${NC}"
    exit 1
  else
    echo -e "${GREEN}✅ Memory OK${NC}"
  fi
fi

# ── Running Container Count ──────────────────────────────────
RUNNING=$(docker ps -q | wc -l | tr -d ' ')
echo ""
echo -e "📦 Running containers: ${BOLD}${RUNNING}${NC}"
if [ "$RUNNING" -gt 30 ]; then
  echo -e "${YELLOW}⚠️  High container count — check if all are needed before building${NC}"
fi

# ── Stale Image Warning ──────────────────────────────────────
DANGLING=$(docker images -f "dangling=true" -q | wc -l | tr -d ' ')
if [ "$DANGLING" -gt 5 ]; then
  echo ""
  echo -e "${YELLOW}⚠️  ${DANGLING} dangling images detected — run: docker image prune -f${NC}"
fi

echo ""
echo -e "${GREEN}${BOLD}✅ Pre-build checks passed — safe to build!${NC}"
echo "======================================="
echo ""
