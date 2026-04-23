#!/bin/bash
# ============================================================================
# HyperCode System Health Check
# ============================================================================
# Validates Docker Compose config, checks container health, resource usage,
# and produces a full system report.
#
# Usage: bash scripts/health-check.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
WARN=0
FAIL=0

log_pass() {
    echo -e "${GREEN}✓${NC} $*"
    ((PASS++))
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
    ((WARN++))
}

log_fail() {
    echo -e "${RED}✗${NC} $*"
    ((FAIL++))
}

header() {
    echo ""
    echo "==================================================================="
    echo "$*"
    echo "==================================================================="
}

# ============================================================================
# VALIDATION
# ============================================================================

header "1. CONFIG VALIDATION"

if docker compose config --quiet 2>/dev/null; then
    log_pass "Compose config is valid"
else
    log_fail "Compose config validation failed"
fi

# ============================================================================
# CONTAINER STATUS
# ============================================================================

header "2. CONTAINER STATUS"

running=$(docker ps --filter "status=running" --format "{{.Names}}" | wc -l)
stopped=$(docker ps --filter "status=exited" --format "{{.Names}}" | wc -l)
total=$((running + stopped))

log_pass "Running: $running containers"
if [ $stopped -gt 0 ]; then
    log_warn "Stopped: $stopped containers"
fi

# Check critical services
critical_services=("hypercode-core" "postgres" "redis" "healer-agent" "prometheus" "grafana")
for service in "${critical_services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" --format "{{.Names}}" | grep -q "$service"; then
        log_pass "$service running"
    else
        log_fail "$service NOT RUNNING"
    fi
done

# ============================================================================
# HEALTH CHECKS
# ============================================================================

header "3. HEALTH CHECK STATUS"

unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | wc -l || echo 0)
no_check=$(docker ps --filter "health=none" --format "{{.Names}}" | wc -l || echo 0)

if [ $unhealthy -eq 0 ]; then
    log_pass "No unhealthy containers"
else
    log_fail "$unhealthy containers report unhealthy"
    docker ps --filter "health=unhealthy" --format "{{.Names}}"
fi

if [ $no_check -gt 5 ]; then
    log_warn "$no_check containers have no healthcheck configured"
fi

# ============================================================================
# RESOURCE USAGE
# ============================================================================

header "4. RESOURCE USAGE"

total_mem=$(docker stats --no-stream --format "{{.MemUsage}}" 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "unknown")
log_pass "Total memory used: $total_mem MB"

# Check for containers near limit
docker ps --format "{{.Names}}\t{{.ID}}" | while read name cid; do
    mem_usage=$(docker inspect "$cid" --format '{{.State.Running}}' 2>/dev/null | grep -q "true" && docker stats --no-stream "$cid" --format "{{.MemUsage}}" | awk -F/ '{print $1}' || echo "0")
    if [ ! -z "$mem_usage" ]; then
        # Simplified: just report large consumers
        if [[ "$mem_usage" =~ [5-9][0-9]{2}M ]]; then
            log_warn "$name using ~$mem_usage"
        fi
    fi
done

# ============================================================================
# DISK SPACE
# ============================================================================

header "5. DISK USAGE"

docker system df --format="table {{.Type}}\t{{.Total}}\t{{.Active}}\t{{.Reclaimable}}" | head -5

reclaimable=$(docker system df --format="{{.Reclaimable}}" | tail -1 | awk '{print $1}')
if [[ "$reclaimable" =~ ^[5-9]G|^[1-9][0-9]G ]]; then
    log_warn "Significant reclaimable space: $reclaimable (consider docker system prune -a)"
else
    log_pass "Disk usage healthy"
fi

# ============================================================================
# VOLUME AUDIT
# ============================================================================

header "6. VOLUME STATUS"

volume_count=$(docker volume ls --format "{{.Name}}" | wc -l)
log_pass "$volume_count volumes present"

# Check for dangling volumes
dangling=$(docker volume ls --filter "dangling=true" --format "{{.Name}}" | wc -l || echo 0)
if [ $dangling -gt 0 ]; then
    log_warn "$dangling dangling volumes (can be safely pruned)"
fi

# ============================================================================
# NETWORK AUDIT
# ============================================================================

header "7. NETWORK TOPOLOGY"

network_count=$(docker network ls --format "{{.Name}}" | grep -E "^hypercode_" | wc -l)
log_pass "$network_count HyperCode networks active"

# Check internal network isolation
internal=$(docker network ls --filter "label.internal=true" --format "{{.Name}}" 2>/dev/null | wc -l || echo 0)
if [ $internal -ge 2 ]; then
    log_pass "Network isolation enforced ($internal internal networks)"
else
    log_warn "Less than 2 internal networks found (review network design)"
fi

# ============================================================================
# SERVICE CONNECTIVITY
# ============================================================================

header "8. SERVICE CONNECTIVITY"

# Test hypercode-core
if curl -s http://localhost:8000/health | grep -q "ok"; then
    log_pass "hypercode-core /health responding"
else
    log_fail "hypercode-core /health failed"
fi

# Test healer-agent
if curl -s http://localhost:8008/health | grep -q "healthy"; then
    log_pass "healer-agent /health responding"
else
    log_fail "healer-agent /health failed"
fi

# Test Prometheus
if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus"; then
    log_pass "prometheus /healthy responding"
else
    log_fail "prometheus /healthy failed"
fi

# Test Grafana
if curl -s http://localhost:3001/api/health | grep -q "ok"; then
    log_pass "grafana /api/health responding"
else
    log_fail "grafana /api/health failed"
fi

# ============================================================================
# SUMMARY
# ============================================================================

header "SUMMARY"

total_checks=$((PASS + WARN + FAIL))
echo ""
echo "Total Checks: $total_checks"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${YELLOW}Warnings: $WARN${NC}"
echo -e "${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "\n${GREEN}System Health: HEALTHY${NC}\n"
    exit 0
elif [ $FAIL -le 2 ]; then
    echo -e "\n${YELLOW}System Health: DEGRADED (minor issues)${NC}\n"
    exit 1
else
    echo -e "\n${RED}System Health: CRITICAL (major issues)${NC}\n"
    exit 2
fi
