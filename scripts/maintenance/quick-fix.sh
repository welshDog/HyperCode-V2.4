#!/bin/bash
# HyperCode V2.0 - Quick Fix Script
# Addresses identified issues from health check

echo "🏥 HyperCode V2.0 Quick Fix Script"
echo "=================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 1. FIX DUAL OLLAMA INSTANCES
# ============================================
echo "${YELLOW}[1/5] Fixing Ollama Dual Instance Issue...${NC}"
echo "Checking for duplicate ollama containers..."

DEAD_OLLAMA=$(docker ps -a --filter "name=hypercode-ollama" --filter "status=exited" -q)
if [ ! -z "$DEAD_OLLAMA" ]; then
    echo "Found dead hypercode-ollama: $DEAD_OLLAMA"
    echo "Removing..."
    docker rm "$DEAD_OLLAMA"
    echo -e "${GREEN}✓ Removed dead hypercode-ollama${NC}"
else
    echo "No dead hypercode-ollama found"
fi

ACTIVE_OLLAMA=$(docker ps --filter "name=ollama" -q | head -1)
if [ ! -z "$ACTIVE_OLLAMA" ]; then
    echo "Active ollama container: $ACTIVE_OLLAMA"
    echo -e "${GREEN}✓ Single ollama instance confirmed${NC}"
else
    echo -e "${RED}✗ No active ollama found - starting from compose${NC}"
    docker-compose up -d hypercode-ollama
fi

echo ""

# ============================================
# 2. FIX GITHUB MCP RESTART LOOP
# ============================================
echo "${YELLOW}[2/5] Investigating GitHub MCP Restart Issue...${NC}"

MCP_GITHUB=$(docker ps --filter "name=mcp-github" -q)
if [ ! -z "$MCP_GITHUB" ]; then
    MCP_STATUS=$(docker inspect "$MCP_GITHUB" --format='{{.State.Status}}')
    echo "GitHub MCP Status: $MCP_STATUS"
    
    # Check logs for errors
    echo "Recent logs:"
    docker logs "$MCP_GITHUB" 2>&1 | tail -5
    
    # Check if token is set
    TOKEN=$(docker inspect "$MCP_GITHUB" --format='{{index .Config.Env "GITHUB_TOKEN"}}' 2>/dev/null)
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}✗ GitHub token not found in environment${NC}"
        echo "Solution: Verify GITHUB_TOKEN in .env file"
    else
        echo -e "${GREEN}✓ GitHub token is set${NC}"
    fi
    
    if [ "$MCP_STATUS" = "restarting" ]; then
        echo "GitHub MCP is in restart loop"
        echo "Attempting restart..."
        docker-compose up -d mcp-github
        echo -e "${YELLOW}ⓘ Monitor with: docker logs -f mcp-github${NC}"
    fi
else
    echo "GitHub MCP container not found"
fi

echo ""

# ============================================
# 3. REMOVE FAILED DOCKER JANITOR
# ============================================
echo "${YELLOW}[3/5] Removing Failed Docker Janitor...${NC}"

JANITOR=$(docker ps -a --filter "name=docker-janitor" --filter "status=exited" -q)
if [ ! -z "$JANITOR" ]; then
    echo "Found dead docker-janitor: $JANITOR"
    docker rm "$JANITOR"
    echo -e "${GREEN}✓ Removed docker-janitor${NC}"
    echo "Note: auto-prune is running as replacement"
else
    echo "Docker-janitor not found or already removed"
fi

echo ""

# ============================================
# 4. SYSTEM CLEANUP
# ============================================
echo "${YELLOW}[4/5] System Cleanup (Optional)...${NC}"

UNUSED_SIZE=$(docker system df | grep "Local Volumes" | awk '{print $3}')
echo "Unused Docker artifacts: $UNUSED_SIZE"
echo ""
echo "Safe cleanup options:"
echo "  1. Prune unused images: docker image prune -a"
echo "  2. Prune build cache: docker builder prune"
echo "  3. Prune unused volumes: docker volume prune"
echo "  4. Full system prune: docker system prune -a"
echo ""
echo -e "${YELLOW}ⓘ Run these manually if needed (not auto-running for safety)${NC}"

echo ""

# ============================================
# 5. HEALTH CHECK SUMMARY
# ============================================
echo "${YELLOW}[5/5] Running Health Checks...${NC}"
echo ""

# Core services
echo "Core Services:"
for service in redis postgres hypercode-core celery-worker; do
    HEALTH=$(docker inspect "$service" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-health")
    STATUS=$(docker inspect "$service" --format='{{.State.Running}}' 2>/dev/null)
    
    if [ "$STATUS" = "true" ]; then
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "  ${GREEN}✓${NC} $service (healthy)"
        elif [ "$HEALTH" = "no-health" ]; then
            echo -e "  ${GREEN}✓${NC} $service (running)"
        else
            echo -e "  ${YELLOW}⚠${NC} $service ($HEALTH)"
        fi
    else
        echo -e "  ${RED}✗${NC} $service (stopped)"
    fi
done

echo ""
echo "Observability Stack:"
for service in prometheus grafana loki tempo; do
    STATUS=$(docker inspect "$service" --format='{{.State.Running}}' 2>/dev/null)
    if [ "$STATUS" = "true" ]; then
        echo -e "  ${GREEN}✓${NC} $service"
    else
        echo -e "  ${RED}✗${NC} $service"
    fi
done

echo ""
echo "Agent Services:"
for service in crew-orchestrator backend-specialist healer-agent; do
    STATUS=$(docker inspect "$service" --format='{{.State.Running}}' 2>/dev/null)
    if [ "$STATUS" = "true" ]; then
        HEALTH=$(docker inspect "$service" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-health")
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "  ${GREEN}✓${NC} $service (healthy)"
        elif [ "$HEALTH" = "no-health" ]; then
            echo -e "  ${GREEN}✓${NC} $service (running)"
        else
            echo -e "  ${YELLOW}⚠${NC} $service ($HEALTH)"
        fi
    else
        echo -e "  ${RED}✗${NC} $service"
    fi
done

echo ""
echo "=================================="
echo -e "${GREEN}Quick Fix Complete!${NC}"
echo ""
echo "Summary:"
echo "  • Removed dead ollama instance"
echo "  • Investigated GitHub MCP issue"
echo "  • Removed docker-janitor"
echo "  • Ran health checks"
echo ""
echo "Next Steps:"
echo "  1. Monitor GitHub MCP: docker logs -f mcp-github"
echo "  2. Check disk space: docker system df"
echo "  3. Review detailed report: cat FULL_HEALTH_CHECK_REPORT.md"
echo "  4. If issues persist: docker-compose logs -f <service>"
echo ""
