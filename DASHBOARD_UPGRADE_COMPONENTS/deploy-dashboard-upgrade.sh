#!/bin/bash
# deploy-dashboard-upgrade.sh
# Deploy Dashboard v2.0 with all new components

set -e

echo "🚀 Starting Dashboard v2.0 Upgrade Deployment"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Docker is running
echo -e "${BLUE}[1/8] Checking Docker...${NC}"
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Stop existing dashboard container
echo -e "${BLUE}[2/8] Stopping existing dashboard...${NC}"
docker compose down hypercode-dashboard 2>/dev/null || true
sleep 2

# Remove old image
echo -e "${BLUE}[3/8] Removing old dashboard image...${NC}"
docker rmi hypercode-v24-dashboard:v2.0 2>/dev/null || true

# Build new image with upgrade components
echo -e "${BLUE}[4/8] Building new dashboard image (v2.0)...${NC}"
docker build \
  -t hypercode-v24-dashboard:v2.0 \
  -f DASHBOARD_UPGRADE_COMPONENTS/Dockerfile.dashboard-v2 \
  .

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build successful${NC}"

# Tag for registry (optional)
# docker tag hypercode-v24-dashboard:v2.0 myregistry/hypercode-dashboard:v2.0

# Start new container
echo -e "${BLUE}[5/8] Starting new dashboard container...${NC}"
docker compose up -d hypercode-dashboard

if [ $? -ne 0 ]; then
    echo -e "${RED}Container startup failed!${NC}"
    exit 1
fi
sleep 3
echo -e "${GREEN}✓ Container started${NC}"

# Verify container is healthy
echo -e "${BLUE}[6/8] Verifying container health...${NC}"
CONTAINER_ID=$(docker ps | grep hypercode-dashboard | awk '{print $1}')
if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}Container not running!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Container running: $CONTAINER_ID${NC}"

# Wait for app to be ready
echo -e "${BLUE}[7/8] Waiting for app to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8088/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ App is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}App did not start in time!${NC}"
        docker logs $CONTAINER_ID
        exit 1
    fi
    sleep 1
done

# Test all endpoints
echo -e "${BLUE}[8/8] Testing all new endpoints...${NC}"

echo "Testing /dashboard..."
curl -s http://localhost:8088/dashboard/ | grep -q "HyperCode Dashboard" && echo "  ✓ /dashboard"

echo "Testing /dashboard/agents..."
curl -s http://localhost:8088/dashboard/agents | grep -q "Agent" && echo "  ✓ /dashboard/agents"

echo "Testing /dashboard/code-ide..."
curl -s http://localhost:8088/dashboard/code-ide | grep -q "IDE" && echo "  ✓ /dashboard/code-ide"

echo "Testing /dashboard/timeline..."
curl -s http://localhost:8088/dashboard/timeline | grep -q "Timeline" && echo "  ✓ /dashboard/timeline"

echo "Testing /dashboard/docker..."
curl -s http://localhost:8088/dashboard/docker | grep -q "Docker" && echo "  ✓ /dashboard/docker"

echo "Testing /dashboard/mcp..."
curl -s http://localhost:8088/dashboard/mcp | grep -q "MCP" && echo "  ✓ /dashboard/mcp"

# Print summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Dashboard v2.0 Deployed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access the dashboard at:"
echo "  🌐 http://localhost:8088/dashboard"
echo ""
echo "Features:"
echo "  ✓ Live Agent Monitor (25 agents, real-time)"
echo "  ✓ Code IDE (execute HyperCode)"
echo "  ✓ Mission Timeline (task visualization)"
echo "  ✓ Docker Zone (container management)"
echo "  ✓ MCP Tool Browser (test MCP tools)"
echo ""
echo "Container ID: $CONTAINER_ID"
echo "Image: hypercode-v24-dashboard:v2.0"
echo "Port: 8088 → 3000"
echo ""
