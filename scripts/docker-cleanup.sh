#!/bin/bash
# ========================================
# Docker System Cleanup & Optimization
# Safely reclaim disk space and optimize build cache
# Safe to run anytime — doesn't affect running containers
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}🧹 Docker System Cleanup & Optimization${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Show before state
echo -e "${YELLOW}📊 Disk Usage BEFORE Cleanup:${NC}"
docker system df
echo ""

# Step 1: Remove dangling images (safe — unused layers)
echo -e "${YELLOW}🗑️  Removing dangling images...${NC}"
DANGLING=$(docker image ls -f "dangling=true" -q | wc -l)
if [ $DANGLING -gt 0 ]; then
  docker image prune --force
  echo -e "${GREEN}✓ Removed $DANGLING dangling images${NC}"
else
  echo -e "${GREEN}✓ No dangling images${NC}"
fi
echo ""

# Step 2: Remove unused images (safe — not in use by running containers)
echo -e "${YELLOW}🗑️  Removing unused images...${NC}"
docker image prune --all --force --filter "until=168h"
echo -e "${GREEN}✓ Removed images older than 7 days${NC}"
echo ""

# Step 3: Remove stopped containers (safe — already exited)
echo -e "${YELLOW}🗑️  Removing stopped containers...${NC}"
STOPPED=$(docker ps -a -f status=exited -q | wc -l)
if [ $STOPPED -gt 0 ]; then
  docker container prune --force
  echo -e "${GREEN}✓ Removed $STOPPED stopped containers${NC}"
else
  echo -e "${GREEN}✓ No stopped containers${NC}"
fi
echo ""

# Step 4: Aggressive build cache prune (safe — can rebuild if needed)
echo -e "${YELLOW}🗑️  Pruning build cache (keeping 5GB)...${NC}"
BEFORE_CACHE=$(docker system df --format "{{.BuildCacheSize}}" 2>/dev/null || echo "unknown")
docker buildx prune --force --keep-storage=5gb 2>/dev/null || docker builder prune --force --keep-storage=5gb
echo -e "${GREEN}✓ Build cache optimized${NC}"
echo ""

# Step 5: Remove unused networks (safe — not in use)
echo -e "${YELLOW}🗑️  Removing unused networks...${NC}"
docker network prune --force
echo -e "${GREEN}✓ Cleaned up unused networks${NC}"
echo ""

# Step 6: Remove unused volumes (optional — keep commented by default)
echo -e "${YELLOW}⚠️  Unused volumes (NOT auto-removed — can contain data):${NC}"
UNUSED_VOLS=$(docker volume ls -f "dangling=true" -q | wc -l)
if [ $UNUSED_VOLS -gt 0 ]; then
  echo -e "${YELLOW}   Found $UNUSED_VOLS dangling volumes${NC}"
  echo -e "${YELLOW}   To remove: docker volume prune --force${NC}"
else
  echo -e "${GREEN}✓ No dangling volumes${NC}"
fi
echo ""

# Show after state
echo -e "${YELLOW}📊 Disk Usage AFTER Cleanup:${NC}"
docker system df
echo ""

# Calculate savings
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Cleanup Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}💡 Recommendations:${NC}"
echo "   • Run weekly to maintain optimal disk usage"
echo "   • Safe for production — doesn't affect running services"
echo "   • If issues occur, docker can rebuild images from cache"
echo ""
