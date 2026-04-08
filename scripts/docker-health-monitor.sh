#!/bin/bash

# Docker Health Monitoring Script for HyperCode Platform
# Monitors container health and reports issues

set -e

COMPOSE_FILE="${1:-docker-compose.yml}"
NAMESPACE="${2:-hypercode}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

echo "🏥 HyperCode Docker Health Monitor"
echo "====================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get all containers from compose file
get_containers() {
    docker-compose -f "$COMPOSE_FILE" ps --services
}

# Check container health
check_container_health() {
    local container=$1
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no_healthcheck")
    echo "$health"
}

# Check container status
check_container_status() {
    local container=$1
    local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
    echo "$status"
}

# Get container restart count
get_restart_count() {
    local container=$1
    docker inspect --format='{{.RestartCount}}' "$container" 2>/dev/null || echo "0"
}

# Get container uptime
get_uptime() {
    local container=$1
    local started=$(docker inspect --format='{{.State.StartedAt}}' "$container" 2>/dev/null)
    if [ -n "$started" ]; then
        local start_time=$(date -d "$started" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$started" +%s 2>/dev/null || echo "0")
        local current_time=$(date +%s)
        local uptime=$((current_time - start_time))
        echo "$uptime seconds"
    else
        echo "N/A"
    fi
}

# Get container resource usage
get_resource_usage() {
    local container=$1
    docker stats --no-stream --format "CPU: {{.CPUPerc}} | Memory: {{.MemUsage}}" "$container" 2>/dev/null || echo "N/A"
}

# Send alert
send_alert() {
    local message=$1
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🚨 HyperCode Alert: $message\"}" \
            2>/dev/null || true
    fi
}

# Main monitoring loop
monitor_containers() {
    local issues_found=0
    
    echo "Checking containers..."
    echo ""
    
    for service in $(get_containers); do
        local container="${NAMESPACE}_${service}_1"
        
        # Try alternative naming schemes
        if ! docker inspect "$container" &>/dev/null; then
            container="$service"
        fi
        
        if ! docker inspect "$container" &>/dev/null; then
            echo -e "${RED}❌ Container $service: NOT FOUND${NC}"
            issues_found=$((issues_found + 1))
            send_alert "Container $service not found"
            continue
        fi
        
        local status=$(check_container_status "$container")
        local health=$(check_container_health "$container")
        local restarts=$(get_restart_count "$container")
        local uptime=$(get_uptime "$container")
        local resources=$(get_resource_usage "$container")
        
        # Status check
        if [ "$status" != "running" ]; then
            echo -e "${RED}❌ $service: $status${NC}"
            issues_found=$((issues_found + 1))
            send_alert "Container $service is $status"
            continue
        fi
        
        # Health check
        if [ "$health" = "unhealthy" ]; then
            echo -e "${RED}❌ $service: UNHEALTHY${NC}"
            echo "   Status: $status | Restarts: $restarts"
            echo "   Uptime: $uptime"
            echo "   Resources: $resources"
            issues_found=$((issues_found + 1))
            send_alert "Container $service is unhealthy"
            
            # Show recent logs
            echo "   Recent logs:"
            docker logs --tail 5 "$container" 2>&1 | sed 's/^/   /'
            echo ""
            continue
        fi
        
        # Warning for high restart count
        if [ "$restarts" -gt 3 ]; then
            echo -e "${YELLOW}⚠️  $service: ${restarts} restarts${NC}"
            echo "   Status: $status | Health: $health"
            echo "   Uptime: $uptime"
            echo "   Resources: $resources"
            echo ""
            continue
        fi
        
        # All good
        if [ "$health" = "healthy" ] || [ "$health" = "no_healthcheck" ]; then
            echo -e "${GREEN}✓ $service: healthy${NC}"
            echo "   Status: $status | Restarts: $restarts"
            echo "   Uptime: $uptime"
            echo "   Resources: $resources"
            echo ""
        fi
    done
    
    echo "====================================="
    if [ $issues_found -eq 0 ]; then
        echo -e "${GREEN}✅ All containers healthy!${NC}"
        return 0
    else
        echo -e "${RED}❌ Found $issues_found issue(s)${NC}"
        return 1
    fi
}

# Check Docker daemon
check_docker() {
    if ! docker info &>/dev/null; then
        echo -e "${RED}❌ Docker daemon not running${NC}"
        exit 1
    fi
}

# Display system resources
show_system_resources() {
    echo ""
    echo "System Resources:"
    echo "-----------------"
    docker system df
    echo ""
}

# Watch mode
watch_mode() {
    while true; do
        clear
        monitor_containers
        echo ""
        echo "Refreshing in 10 seconds... (Ctrl+C to stop)"
        sleep 10
    done
}

# Main
main() {
    check_docker
    
    case "${3:-}" in
        --watch|-w)
            watch_mode
            ;;
        --resources|-r)
            show_system_resources
            ;;
        *)
            monitor_containers
            ;;
    esac
}

main "$@"
