#!/bin/bash
# ========================================
# TRAE IDE — ONE-COMMAND START SCRIPT
# Gets you training agents in 60 seconds
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}🎓 TRAE IDE — Agent Training Setup${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Step 1: Check if core system is running
echo -e "${YELLOW}[1/4] Checking core services...${NC}"
if ! docker ps | grep -q hypercode-core; then
  echo -e "${RED}✗ hypercode-core not running${NC}"
  echo "  Start with: docker compose up -d"
  exit 1
fi
echo -e "${GREEN}✓ Core services running${NC}"
echo ""

# Step 2: Start Trae services
echo -e "${YELLOW}[2/4] Starting Trae IDE services...${NC}"
docker compose -f docker-compose.yml -f docker-compose.trae.yml up -d trae-ide agent-training-api skill-repository 2>/dev/null || {
  echo -e "${YELLOW}Building services (first time only)...${NC}"
  docker compose -f docker-compose.yml -f docker-compose.trae.yml build --no-cache trae-ide agent-training-api
  docker compose -f docker-compose.yml -f docker-compose.trae.yml up -d
}
echo -e "${GREEN}✓ Services starting${NC}"
echo ""

# Step 3: Wait for services
echo -e "${YELLOW}[3/4] Waiting for services to be ready (30s)...${NC}"
sleep 30

# Check health
for i in {1..5}; do
  if curl -s http://localhost:3500/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Trae IDE ready${NC}"
    break
  fi
  if [ $i -lt 5 ]; then
    echo -n "."
    sleep 5
  fi
done
echo ""

# Step 4: Show access info
echo -e "${YELLOW}[4/4] Configuration complete${NC}"
echo ""

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ TRAE IDE IS READY!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}📚 ACCESS OPTIONS:${NC}"
echo ""
echo "  🌐 WEB DASHBOARD (Recommended for beginners):"
echo "     ${GREEN}http://localhost:3500${NC}"
echo "     • Point-and-click agent training"
echo "     • Visual conversation history"
echo "     • Real-time skill tracker"
echo ""

echo "  💻 CLI TERMINAL (Recommended for power users):"
echo "     ${GREEN}python trae-agent-bridge.py${NC}"
echo "     Commands:"
echo "     • chat frontend-specialist \"Create a form\""
echo "     • train backend-specialist \"FastAPI patterns\""
echo "     • team \"Code review this implementation\""
echo "     • status devops-engineer"
echo ""

echo "  🔌 API ENDPOINTS (For developers):"
echo "     POST ${GREEN}http://localhost:8097/chat${NC}"
echo "     POST ${GREEN}http://localhost:8097/train${NC}"
echo "     WS  ${GREEN}ws://localhost:8097/ws/agent/backend-specialist${NC}"
echo ""

echo -e "${YELLOW}🎯 QUICK EXAMPLES:${NC}"
echo ""
echo "  1. Web interface (easiest):"
echo "     Open http://localhost:3500 in your browser"
echo ""
echo "  2. Chat with an agent:"
echo "     ${GREEN}python trae-agent-bridge.py${NC}"
echo "     ${GREEN}trae> chat backend-specialist \"Show me a FastAPI example\"${NC}"
echo ""
echo "  3. Train new skill:"
echo "     ${GREEN}trae> train qa-engineer \"Test automation patterns\"${NC}"
echo ""
echo "  4. Multi-agent collaboration:"
echo "     ${GREEN}trae> team \"Review this code for security issues\"${NC}"
echo ""

echo -e "${YELLOW}📊 RUNNING SERVICES:${NC}"
docker compose ps | grep -E "trae-ide|agent-training|skill-repo"
echo ""

echo -e "${YELLOW}📖 FULL DOCUMENTATION:${NC}"
echo "  Read: ${GREEN}TRAE_IDE_SETUP_GUIDE.md${NC}"
echo ""

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}Your agents are ready for training! 🚀${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
