#!/bin/bash

# Docker Cleanup Script for HyperCode
# Safely removes unused Docker resources

set -e

echo "🧹 HyperCode Docker Cleanup Utility"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Show current disk usage
show_disk_usage() {
    echo "Current Docker disk usage:"
    docker system df
    echo ""
}

# Clean stopped containers
clean_stopped_containers() {
    echo "Removing stopped containers..."
    local count=$(docker ps -a -q -f status=exited | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        docker container prune -f
        echo -e "${GREEN}✓ Removed $count stopped container(s)${NC}"
    else
        echo "No stopped containers to remove"
    fi
    echo ""
}

# Clean dangling images
clean_dangling_images() {
    echo "Removing dangling images..."
    local count=$(docker images -f "dangling=true" -q | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        docker image prune -f
        echo -e "${GREEN}✓ Removed $count dangling image(s)${NC}"
    else
        echo "No dangling images to remove"
    fi
    echo ""
}

# Clean unused volumes
clean_unused_volumes() {
    echo "Removing unused volumes..."
    local count=$(docker volume ls -qf dangling=true | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        docker volume prune -f
        echo -e "${GREEN}✓ Removed $count unused volume(s)${NC}"
    else
        echo "No unused volumes to remove"
    fi
    echo ""
}

# Clean build cache
clean_build_cache() {
    echo "Removing build cache..."
    docker builder prune -f
    echo -e "${GREEN}✓ Build cache cleaned${NC}"
    echo ""
}

# Clean unused networks
clean_unused_networks() {
    echo "Removing unused networks..."
    docker network prune -f
    echo -e "${GREEN}✓ Unused networks removed${NC}"
    echo ""
}

# Clean old images (keep last 3 versions)
clean_old_images() {
    echo "Removing old image versions (keeping last 3)..."
    
    for repo in hypercode-core crew-orchestrator frontend-specialist backend-specialist database-architect qa-engineer devops-engineer security-engineer system-architect project-strategist; do
        local images=$(docker images --format "{{.ID}}" "$repo" 2>/dev/null | tail -n +4)
        if [ -n "$images" ]; then
            echo "Cleaning old versions of $repo..."
            echo "$images" | xargs -r docker rmi -f 2>/dev/null || true
        fi
    done
    echo ""
}

# Deep clean (warning required)
deep_clean() {
    echo -e "${YELLOW}⚠️  WARNING: This will remove ALL unused Docker resources${NC}"
    echo "This includes:"
    echo "  - All stopped containers"
    echo "  - All networks not used by at least one container"
    echo "  - All dangling images"
    echo "  - All dangling build cache"
    echo ""
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        docker system prune -a -f --volumes
        echo -e "${GREEN}✓ Deep clean complete${NC}"
    else
        echo "Deep clean cancelled"
    fi
    echo ""
}

# Remove HyperCode specific resources
clean_hypercode() {
    echo -e "${YELLOW}⚠️  WARNING: This will remove all HyperCode containers and volumes${NC}"
    echo ""
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo "Stopping and removing HyperCode containers..."
        docker-compose -f docker-compose.yml down -v 2>/dev/null || true
        docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
        docker-compose -f docker-compose.agents.yml down -v 2>/dev/null || true
        docker-compose -f docker-compose.monitoring.yml down -v 2>/dev/null || true
        
        echo "Removing HyperCode images..."
        docker images | grep hypercode | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
        
        echo -e "${GREEN}✓ HyperCode resources cleaned${NC}"
    else
        echo "Cleanup cancelled"
    fi
    echo ""
}

# Show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --all              Clean all unused resources (default)"
    echo "  --containers       Clean stopped containers only"
    echo "  --images           Clean dangling images only"
    echo "  --volumes          Clean unused volumes only"
    echo "  --cache            Clean build cache only"
    echo "  --networks         Clean unused networks only"
    echo "  --deep             Deep clean (removes ALL unused resources)"
    echo "  --hypercode        Remove all HyperCode specific resources"
    echo "  --help             Show this help message"
    echo ""
}

# Main
main() {
    show_disk_usage
    
    case "${1:-all}" in
        --containers)
            clean_stopped_containers
            ;;
        --images)
            clean_dangling_images
            ;;
        --volumes)
            clean_unused_volumes
            ;;
        --cache)
            clean_build_cache
            ;;
        --networks)
            clean_unused_networks
            ;;
        --deep)
            deep_clean
            ;;
        --hypercode)
            clean_hypercode
            ;;
        --all|all)
            clean_stopped_containers
            clean_dangling_images
            clean_unused_volumes
            clean_build_cache
            clean_unused_networks
            clean_old_images
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    
    echo "===================================="
    echo "After cleanup:"
    show_disk_usage
    echo -e "${GREEN}✅ Cleanup complete!${NC}"
}

main "$@"
