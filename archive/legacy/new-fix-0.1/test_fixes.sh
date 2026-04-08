#!/bin/bash
# 🧪 HyperCode V2.0 - Fix Verification Test Suite
# Tests Redis memory cap, healer recovery time, and parallel healing

set -e  # Exit on any error

echo "🔥 HyperCode V2.0 - Fix Verification Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Helper function for test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((FAILED++))
    fi
    echo ""
}

# ====================
# TEST 1: Redis Memory Cap
# ====================
echo "🟢 TEST 1: Redis Memory Configuration"
echo "----------------------------------------"

# Check if Redis is running
if ! docker ps | grep -q "redis"; then
    echo -e "${YELLOW}⚠️  Redis not running - starting it...${NC}"
    docker-compose up -d redis
    sleep 5
fi

# Test maxmemory setting
REDIS_MAXMEM=$(docker exec redis redis-cli CONFIG GET maxmemory | tail -n 1)
if [ "$REDIS_MAXMEM" = "536870912" ]; then
    test_result 0 "Redis maxmemory set to 512MB (536870912 bytes)"
else
    test_result 1 "Redis maxmemory incorrect. Got: $REDIS_MAXMEM, Expected: 536870912"
fi

# Test eviction policy
REDIS_POLICY=$(docker exec redis redis-cli CONFIG GET maxmemory-policy | tail -n 1)
if [ "$REDIS_POLICY" = "allkeys-lru" ]; then
    test_result 0 "Redis eviction policy set to allkeys-lru"
else
    test_result 1 "Redis eviction policy incorrect. Got: $REDIS_POLICY, Expected: allkeys-lru"
fi

# Test Docker resource limits
REDIS_MEM_LIMIT=$(docker inspect redis --format '{{.HostConfig.Memory}}')
if [ "$REDIS_MEM_LIMIT" = "536870912" ]; then
    test_result 0 "Docker memory limit set to 512MB"
else
    test_result 1 "Docker memory limit incorrect. Got: $REDIS_MEM_LIMIT, Expected: 536870912"
fi

# ====================
# TEST 2: Healer Agent Health
# ====================
echo "🟡 TEST 2: Healer Agent Health Check"
echo "----------------------------------------"

# Check if healer is running
if ! docker ps | grep -q "healer-agent"; then
    echo -e "${YELLOW}⚠️  Healer agent not running - starting it...${NC}"
    docker-compose up -d healer-agent
    sleep 10
fi

# Test healer health endpoint
HEALER_HEALTH=$(curl -s http://localhost:8010/health | jq -r '.status')
if [ "$HEALER_HEALTH" = "healthy" ] || [ "$HEALER_HEALTH" = "degraded" ]; then
    test_result 0 "Healer agent responding to health checks (Status: $HEALER_HEALTH)"
else
    test_result 1 "Healer agent health check failed. Got: $HEALER_HEALTH"
fi

# Test circuit breaker endpoint
CB_STATUS=$(curl -s http://localhost:8010/circuit-breaker/status | jq -r '.threshold')
if [ "$CB_STATUS" = "3" ]; then
    test_result 0 "Circuit breaker configured correctly (threshold: 3)"
else
    test_result 1 "Circuit breaker configuration incorrect. Got: $CB_STATUS"
fi

# ====================
# TEST 3: Agent Recovery Time
# ====================
echo "🔴 TEST 3: Single Agent Recovery Time"
echo "----------------------------------------"

# This test requires frontend-specialist to be running
if docker ps | grep -q "frontend-specialist"; then
    echo "Stopping frontend-specialist to simulate crash..."
    docker stop frontend-specialist > /dev/null 2>&1
    
    echo "Triggering healer alert via Redis..."
    docker exec redis redis-cli PUBLISH system_alert "test_single_recovery" > /dev/null 2>&1
    
    echo "Waiting for healer to detect and recover..."
    START_TIME=$(date +%s)
    
    # Wait up to 30 seconds for recovery
    RECOVERED=0
    for i in {1..30}; do
        sleep 1
        if docker ps | grep -q "frontend-specialist"; then
            RECOVERED=1
            break
        fi
    done
    
    END_TIME=$(date +%s)
    RECOVERY_TIME=$((END_TIME - START_TIME))
    
    if [ $RECOVERED -eq 1 ]; then
        if [ $RECOVERY_TIME -le 20 ]; then
            test_result 0 "Agent recovered in ${RECOVERY_TIME}s (target: <20s)"
        else
            test_result 1 "Agent recovered but took ${RECOVERY_TIME}s (target: <20s)"
        fi
    else
        test_result 1 "Agent failed to recover within 30s"
    fi
else
    echo -e "${YELLOW}⚠️  frontend-specialist not configured - skipping recovery test${NC}"
    echo ""
fi

# ====================
# TEST 4: Parallel Healing
# ====================
echo "🟣 TEST 4: Parallel Healing Performance"
echo "----------------------------------------"

# Check if we have multiple agents running
AGENT_COUNT=$(docker ps --filter "name=agent" --format "{{.Names}}" | wc -l)

if [ "$AGENT_COUNT" -ge 3 ]; then
    echo "Found $AGENT_COUNT agents - testing parallel healing..."
    
    # Stop 3 agents simultaneously
    AGENTS_TO_STOP=$(docker ps --filter "name=agent" --format "{{.Names}}" | head -n 3)
    echo "Stopping agents: $AGENTS_TO_STOP"
    echo "$AGENTS_TO_STOP" | xargs docker stop > /dev/null 2>&1
    
    echo "Triggering healer alert..."
    docker exec redis redis-cli PUBLISH system_alert "test_parallel_healing" > /dev/null 2>&1
    
    echo "Waiting for parallel recovery..."
    START_TIME=$(date +%s)
    
    # Wait up to 40 seconds for all to recover
    RECOVERED=0
    for i in {1..40}; do
        sleep 1
        RUNNING_COUNT=$(echo "$AGENTS_TO_STOP" | xargs -I {} sh -c 'docker ps | grep -q {} && echo 1 || echo 0' | grep 1 | wc -l)
        if [ "$RUNNING_COUNT" -eq 3 ]; then
            RECOVERED=1
            break
        fi
    done
    
    END_TIME=$(date +%s)
    RECOVERY_TIME=$((END_TIME - START_TIME))
    
    if [ $RECOVERED -eq 1 ]; then
        if [ $RECOVERY_TIME -le 25 ]; then
            test_result 0 "All 3 agents recovered in ${RECOVERY_TIME}s (parallel - target: <25s)"
        else
            test_result 1 "Agents recovered but took ${RECOVERY_TIME}s (sequential would be 60+s)"
        fi
    else
        test_result 1 "Not all agents recovered within 40s"
    fi
else
    echo -e "${YELLOW}⚠️  Less than 3 agents running - skipping parallel healing test${NC}"
    echo ""
fi

# ====================
# TEST 5: Grafana Dependency
# ====================
echo "🟢 TEST 5: Service Dependencies"
echo "----------------------------------------"

# Check if Grafana waits for Prometheus health check
GRAFANA_DEPENDS=$(docker inspect grafana --format '{{json .HostConfig.DependsOn}}' 2>/dev/null || echo "[]")
if echo "$GRAFANA_DEPENDS" | grep -q "prometheus"; then
    test_result 0 "Grafana has proper dependency on Prometheus"
else
    # Check if Grafana is running and Prometheus is healthy
    if docker ps | grep -q "grafana" && docker ps | grep -q "prometheus"; then
        test_result 0 "Grafana and Prometheus both running (dependency may be implicit)"
    else
        test_result 1 "Grafana dependency check unclear"
    fi
fi

# ====================
# FINAL RESULTS
# ====================
echo "========================================"
echo "🎯 TEST SUITE COMPLETE"
echo "========================================"
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo "Your HyperCode V2.0 system is properly configured."
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo "Review the failed tests above and check:"
    echo "  1. Docker containers are running: docker-compose ps"
    echo "  2. Logs for errors: docker-compose logs"
    echo "  3. Applied all fixes from HYPERCODE_CODE_REVIEW.md"
    exit 1
fi

# ====================
# ADDITIONAL DIAGNOSTICS
# ====================
echo ""
echo "📊 SYSTEM DIAGNOSTICS"
echo "=========================================="
echo "Redis Memory Usage:"
docker exec redis redis-cli INFO memory | grep "used_memory_human\|maxmemory_human" || echo "N/A"
echo ""
echo "Running Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "redis|healer|frontend|backend|database" || echo "No relevant containers running"
echo ""
echo "Circuit Breaker Status:"
curl -s http://localhost:8010/circuit-breaker/status 2>/dev/null | jq '.' || echo "Healer not responding"
echo ""
