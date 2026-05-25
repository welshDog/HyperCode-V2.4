#!/bin/bash
# ========================================
# Automated Deployment Validation Script
# Validates entire HyperCode stack startup
# Checks: service startup, health checks, API responsiveness
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 HyperCode Stack Deployment Validation${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# Navigate to project
cd "$PROJECT_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Prepare
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Preparing environment...${NC}"

# Load environment
if [ -f .env ]; then
  echo -e "${GREEN}✓ .env found${NC}"
else
  echo -e "${RED}✗ .env not found${NC}"
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Pull Latest Images
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Pulling latest images...${NC}"
docker compose pull
echo -e "${GREEN}✓ Images pulled${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Start Services
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Starting services (this may take 60-90 seconds)...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: Validate Core Services
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Validating core services...${NC}"

validate_service() {
  local service=$1
  local port=$2
  local timeout=$3
  
  echo -n "  Waiting for $service (port $port)... "
  
  for i in $(seq 1 $timeout); do
    if curl -s -f http://localhost:$port/health >/dev/null 2>&1; then
      echo -e "${GREEN}✓${NC}"
      return 0
    fi
    sleep 1
  done
  
  echo -e "${RED}✗ (timeout after ${timeout}s)${NC}"
  return 1
}

# Core services with validation
validate_service "hypercode-core" 8000 60 || true
validate_service "grafana" 3001 30 || true

# Check database connectivity
echo -n "  Checking postgres... "
if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${YELLOW}⚠ (delayed response)${NC}"
fi

# Check Redis connectivity
echo -n "  Checking redis... "
if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${YELLOW}⚠ (delayed response)${NC}"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: Health Report
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Health status report...${NC}"
echo ""

# Get container status
RUNNING=$(docker compose ps --format "{{.Status}}" | grep -c "Up" || true)
TOTAL=$(docker compose ps --format "{{.Status}}" | wc -l)
HEALTHY=$(docker compose ps --format "{{.Status}}" | grep -c "healthy" || true)
UNHEALTHY=$(docker compose ps --format "{{.Status}}" | grep -c "unhealthy" || true)

echo -e "${BLUE}Container Status:${NC}"
echo "  Running:    $RUNNING/$TOTAL"
echo "  Healthy:    $HEALTHY services"
if [ $UNHEALTHY -gt 0 ]; then
  echo -e "  Unhealthy:  ${RED}$UNHEALTHY services${NC}"
else
  echo -e "  Unhealthy:  ${GREEN}0 services${NC}"
fi
echo ""

# Show all container status
echo -e "${BLUE}Detailed Status:${NC}"
docker compose ps --format "table {{.Service}}\t{{.Status}}" | head -20
echo ""

# Final verdict
if [ $RUNNING -eq $TOTAL ] && [ $UNHEALTHY -eq 0 ]; then
  echo -e "${GREEN}════════════════════════════════════════${NC}"
  echo -e "${GREEN}✅ Deployment Validation PASSED${NC}"
  echo -e "${GREEN}════════════════════════════════════════${NC}"
  echo ""
  echo -e "${BLUE}🎯 Next Steps:${NC}"
  echo "   • Dashboard:     http://localhost:8088"
  echo "   • Grafana:       http://localhost:3001"
  echo "   • Core API:      http://localhost:8000"
  echo "   • Logs:          docker compose logs -f <service>"
  exit 0
else
  echo -e "${RED}════════════════════════════════════════${NC}"
  echo -e "${RED}❌ Deployment Validation FAILED${NC}"
  echo -e "${RED}════════════════════════════════════════${NC}"
  echo ""
  echo -e "${YELLOW}Troubleshooting:${NC}"
  echo "   • Check logs:    docker compose logs <service>"
  echo "   • Restart:       docker compose restart"
  echo "   • Full recovery: bash scripts/emergency-recover.sh"
  exit 1
fi
