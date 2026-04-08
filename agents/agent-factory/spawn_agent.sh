#!/bin/bash
# 🎯 HyperCode V2.0 Agent Factory - On-Demand Agent Spawner
#
# Spin up individual agents without manual docker compose syntax.
# Usage: ./spawn_agent.sh <agent-name>
#
# ⚠️  REQUIRES: docker compose + bash (or WSL on Windows)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

AGENT="$1"

# List of all available agents
AVAILABLE_AGENTS=(
  "crew-orchestrator"
  "coder-agent"
  "tips-tricks-writer"
  "healer-agent"
  "project-strategist"
  "frontend-specialist"
  "backend-specialist"
  "database-architect"
  "qa-engineer"
  "devops-engineer"
  "security-engineer"
  "system-architect"
  "test-agent"
)

# Print usage
usage() {
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}HyperCode V2.0 - Agent Factory (Spawner)${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "${YELLOW}Usage:${NC}"
  echo "  ./spawn_agent.sh <agent-name>"
  echo ""
  echo -e "${YELLOW}Examples:${NC}"
  echo "  ./spawn_agent.sh coder-agent"
  echo "  ./spawn_agent.sh healer-agent"
  echo "  ./spawn_agent.sh crew-orchestrator"
  echo ""
  echo -e "${YELLOW}Available Agents:${NC}"
  for agent in "${AVAILABLE_AGENTS[@]}"; do
    echo "  • $agent"
  done
  echo ""
  echo -e "${YELLOW}Quick Starter Combos:${NC}"
  echo "  # Lean stack (fits 4GB RAM):"
  echo "  docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d"
  echo ""
  echo "  # Individual agents:"
  echo "  ./spawn_agent.sh coder-agent"
  echo "  ./spawn_agent.sh healer-agent"
  echo ""
}

# Check if agent name provided
if [ -z "$AGENT" ]; then
  echo -e "${RED}❌ Missing agent name!${NC}"
  echo ""
  usage
  exit 1
fi

# Check if agent is valid
valid=0
for available in "${AVAILABLE_AGENTS[@]}"; do
  if [ "$available" = "$AGENT" ]; then
    valid=1
    break
  fi
done

if [ $valid -eq 0 ]; then
  echo -e "${RED}❌ Unknown agent: $AGENT${NC}"
  echo ""
  usage
  exit 1
fi

# Check if agent already running
if docker ps --format '{{.Names}}' | grep -q "^${AGENT}$"; then
  echo -e "${GREEN}✅ $AGENT is already running!${NC}"
  echo ""
  echo -e "${YELLOW}Status:${NC}"
  docker ps --filter "name=^${AGENT}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  echo ""
  echo -e "${YELLOW}Commands:${NC}"
  echo "  View logs:  docker logs $AGENT --tail 50 -f"
  echo "  Restart:    docker restart $AGENT"
  echo "  Stop:       docker stop $AGENT"
  echo ""
  exit 0
fi

# Check if agent is stopped (exists but not running)
if docker ps -a --format '{{.Names}}' | grep -q "^${AGENT}$"; then
  echo -e "${YELLOW}⏸️  $AGENT exists but is stopped. Restarting...${NC}"
  docker restart "$AGENT"
  sleep 2
  
  # Check if restart was successful
  if docker ps --format '{{.Names}}' | grep -q "^${AGENT}$"; then
    echo -e "${GREEN}✅ $AGENT restarted successfully!${NC}"
    docker ps --filter "name=^${AGENT}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${YELLOW}Quick Links:${NC}"
    echo "  View logs:  docker logs $AGENT --tail 50 -f"
    echo "  Details:    docker inspect $AGENT | jq '.[] | {State, Config.Image, HostConfig.PortBindings}'"
    echo ""
    exit 0
  else
    echo -e "${RED}❌ Failed to restart $AGENT. Check logs with:${NC}"
    echo "  docker logs $AGENT"
    exit 1
  fi
fi

# Agent doesn't exist - start it with profile
echo -e "${BLUE}🚀 Spawning $AGENT...${NC}"
echo "   Using: docker compose --profile agents up -d $AGENT"
echo ""

# Make sure compose file exists
if [ ! -f "docker-compose.yml" ]; then
  echo -e "${RED}❌ Error: docker-compose.yml not found in current directory${NC}"
  echo "   Make sure you're in the HyperCode-V2.0 directory"
  exit 1
fi

# Spawn agent
docker compose --profile agents up -d "$AGENT" 2>&1

# Wait for container to start
echo -e "${YELLOW}⏳ Waiting for $AGENT to initialize...${NC}"
sleep 3

# Check if spawn was successful
if docker ps --format '{{.Names}}' | grep -q "^${AGENT}$"; then
  echo -e "${GREEN}✅ $AGENT launched successfully!${NC}"
  echo ""
  
  # Get container info
  CONTAINER_INFO=$(docker ps --filter "name=^${AGENT}$" --format "{{.Ports}}")
  
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}Agent Details:${NC}"
  docker ps --filter "name=^${AGENT}$" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
  echo ""
  echo -e "${YELLOW}Ports:${NC}"
  docker inspect "$AGENT" --format='{{range $p, $conf := .NetworkSettings.Ports}}{{$p}} -> {{(index $conf 0).HostPort}}{{println}}{{end}}'
  echo ""
  echo -e "${YELLOW}Commands:${NC}"
  echo "  📋 View logs:        docker logs $AGENT --tail 100 -f"
  echo "  🔍 Inspect config:   docker inspect $AGENT"
  echo "  ⏹️  Stop:             docker stop $AGENT"
  echo "  🔄 Restart:          docker restart $AGENT"
  echo "  🗑️  Remove:           docker rm $AGENT"
  echo ""
  echo -e "${YELLOW}Health Check:${NC}"
  echo "  GET http://localhost:8000/health (typical agent health endpoint)"
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
  
else
  echo -e "${RED}❌ Failed to spawn $AGENT. Check logs:${NC}"
  docker logs "$AGENT" --tail 50
  exit 1
fi
