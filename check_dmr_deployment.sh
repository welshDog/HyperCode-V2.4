#!/usr/bin/env bash
# DMR Integration Deployment Checklist
# Run this to verify all files are in place and Agent X is ready

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Docker Model Runner (DMR) Integration Deployment Checklist"
echo "==========================================================="
echo ""

# Counter
PASS=0
FAIL=0

# Check function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        ((FAIL++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        ((FAIL++))
    fi
}

# 1. Core Implementation Files
echo "1. Core Implementation"
echo "─────────────────────"
check_file "agents/agent-x/agentx/dmr_client.py"
check_file "agents/agent-x/agentx/integration_example.py"
check_file "agents/agent-x/dmr_requirements.txt"
echo ""

# 2. Deployment Configuration
echo "2. Deployment Configuration"
echo "──────────────────────────"
check_file "docker-compose.dmr.yml"
check_file "Dockerfile"  # Existing, should not change
echo ""

# 3. Validation & Testing
echo "3. Validation & Testing"
echo "──────────────────────"
check_file "test_dmr_client.py"
echo ""

# 4. Documentation
echo "4. Documentation"
echo "────────────────"
check_file "AGENT_X_DMR_INTEGRATION.md"
check_file "AGENT_X_DMR_SUMMARY.md"
check_file "AGENT_X_DMR_ARCHITECTURE.md"
check_file "DMR_DELIVERY_SUMMARY.txt"
echo ""

# 5. Dependencies
echo "5. Dependencies Check"
echo "─────────────────────"
if grep -q "aiohttp" agents/agent-x/requirements.txt 2>/dev/null; then
    echo -e "${GREEN}✓${NC} aiohttp in requirements.txt"
    ((PASS++))
else
    echo -e "${YELLOW}⚠${NC} Add dmr_requirements.txt to requirements.txt"
    ((FAIL++))
fi
echo ""

# 6. Docker Requirements
echo "6. Docker Requirements"
echo "─────────────────────"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}')
    echo -e "${GREEN}✓${NC} Docker installed (version: $DOCKER_VERSION)"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker not installed"
    ((FAIL++))
fi

if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose available"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker Compose not available"
    ((FAIL++))
fi
echo ""

# 7. Summary
echo "Summary"
echo "═══════"
TOTAL=$((PASS + FAIL))
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
echo -e "Total:  $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Add dmr_requirements.txt to requirements.txt:"
    echo "   cat agents/agent-x/dmr_requirements.txt >> agents/agent-x/requirements.txt"
    echo ""
    echo "2. Validate DMR connectivity:"
    echo "   python test_dmr_client.py"
    echo ""
    echo "3. Build updated Agent X:"
    echo "   docker build -t hypercode-v24-agent-x:dmr -f agents/agent-x/Dockerfile ."
    echo ""
    echo "4. Deploy with DMR:"
    echo "   docker compose -f docker-compose.yml -f docker-compose.dmr.yml up agent-x"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Review above and correct.${NC}"
    exit 1
fi
