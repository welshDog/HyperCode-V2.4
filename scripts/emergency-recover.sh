#!/bin/bash
# ========================================
# Emergency Recovery Script
# Full system reset + clean restart
# Use when: containers stuck, database corrupted, memory leak, etc.
# WARNING: Resets all containers — data in volumes is safe
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}════════════════════════════════════════${NC}"
echo -e "${RED}🆘 EMERGENCY RECOVERY MODE${NC}"
echo -e "${RED}════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠️  This will:${NC}"
echo "   • Stop all running containers"
echo "   • Remove all containers"
echo "   • Clear build cache and dangling images"
echo "   • Restart fresh stack"
echo ""
echo -e "${YELLOW}This will NOT:${NC}"
echo "   • Delete volumes or data"
echo "   • Delete your source code"
echo "   • Delete the .env file"
echo ""

read -p "Are you sure? Type 'RECOVER' to proceed: " CONFIRM

if [ "$CONFIRM" != "RECOVER" ]; then
  echo -e "${GREEN}Cancelled.${NC}"
  exit 0
fi

echo ""
echo -e "${YELLOW}Starting emergency recovery...${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Step 1: Stop all containers gracefully
echo -e "${YELLOW}[1/5] Stopping all containers...${NC}"
docker compose down --timeout 30 --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✓ Stopped${NC}"
echo ""

# Step 2: Remove all containers (just in case)
echo -e "${YELLOW}[2/5] Removing stuck containers...${NC}"
docker ps -a -q | xargs -r docker rm -f 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned${NC}"
echo ""

# Step 3: Aggressive system cleanup
echo -e "${YELLOW}[3/5] Aggressive system cleanup...${NC}"
docker system prune --force --all 2>/dev/null || true
docker buildx prune --force --keep-storage=5gb 2>/dev/null || true
echo -e "${GREEN}✓ Cache cleared${NC}"
echo ""

# Step 4: Fresh pull and rebuild
echo -e "${YELLOW}[4/5] Pulling fresh images...${NC}"
docker compose pull
echo -e "${GREEN}✓ Images pulled${NC}"
echo ""

# Step 5: Start clean
echo -e "${YELLOW}[5/5] Starting fresh stack...${NC}"
docker compose up -d
echo ""

# Wait for stabilization
echo -e "${YELLOW}Waiting for services to stabilize (30s)...${NC}"
sleep 30

# Validate
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}Status Report:${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
docker compose ps --format "table {{.Service}}\t{{.Status}}"
echo ""

RUNNING=$(docker compose ps --format "{{.Status}}" | grep -c "Up" || true)
TOTAL=$(docker compose ps --format "{{.Status}}" | wc -l)

if [ $RUNNING -eq $TOTAL ]; then
  echo -e "${GREEN}✅ Recovery complete! All services online.${NC}"
  exit 0
else
  echo -e "${YELLOW}⚠️  Some services may still be starting...${NC}"
  echo "    Check again in 30 seconds: docker compose ps"
  exit 0
fi
