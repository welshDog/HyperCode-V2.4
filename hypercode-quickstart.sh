#!/bin/bash

# HyperCode-V2.4 Quick Start Script
# Usage: ./hypercode-quickstart.sh [core|full|agents|health|all]

set -e

COMMAND=${1:-core}
HC_DATA_ROOT="${HC_DATA_ROOT:-./_HC_DATA}"

echo "🚀 HyperCode-V2.4 Docker Ecosystem Starter"
echo "==========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Validate Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker 27+."
    exit 1
fi

# Validate Docker Compose
if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose not found. Please install Docker Compose 2.20+."
    exit 1
fi

log_info "Docker $(docker --version | awk '{print $3}')"
log_info "Docker Compose $(docker compose version --short)"
echo ""

# Create networks
create_networks() {
    log_info "Creating docker networks..."
    docker network create hypercode_backend_net 2>/dev/null || log_warn "backend-net already exists"
    docker network create hypercode_data_net 2>/dev/null || log_warn "data-net already exists"
    docker network create hypercode_agents_net 2>/dev/null || log_warn "agents-net already exists"
    docker network create hypercode_obs_net 2>/dev/null || log_warn "obs-net already exists"
    docker network create hypercode_frontend_net 2>/dev/null || log_warn "frontend-net already exists"
    echo ""
}

# Create data directories
create_data_dirs() {
    log_info "Creating data directories at $HC_DATA_ROOT..."
    mkdir -p "$HC_DATA_ROOT"/{redis,postgres,ollama,prometheus,grafana,loki,tempo,chroma,alertmanager,trivy}
    chmod -R 755 "$HC_DATA_ROOT"
    echo ""
}

# Check .env file
check_env() {
    if [ ! -f "./HyperCode-V2.4/.env" ]; then
        log_warn ".env file not found. Copying from .env.example..."
        cp "./HyperCode-V2.4/.env.example" "./HyperCode-V2.4/.env"
        log_warn "Please edit ./HyperCode-V2.4/.env with your secrets (Stripe, GitHub, API keys)"
    fi
}

# Start core services
start_core() {
    log_info "Starting core services (redis, postgres, hypercode-core, ollama, celery)..."
    cd ./HyperCode-V2.4
    docker compose -f docker-compose.core.yml up -d --pull always
    cd ..
    
    log_info "Waiting for services to be healthy (60s)..."
    sleep 30
    
    if docker compose -f ./HyperCode-V2.4/docker-compose.core.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis is healthy"
    else
        log_warn "Redis not ready yet"
    fi
    
    if docker compose -f ./HyperCode-V2.4/docker-compose.core.yml exec postgres pg_isready > /dev/null 2>&1; then
        log_info "PostgreSQL is healthy"
    else
        log_warn "PostgreSQL not ready yet"
    fi
    
    sleep 30
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_info "HyperCode-Core is healthy → http://localhost:8000"
    else
        log_warn "HyperCode-Core still starting... check logs: docker compose logs hypercode-core"
    fi
    
    echo ""
    log_info "Dashboard available at http://localhost:8088"
    echo ""
}

# Start observability stack
start_observability() {
    log_info "Starting observability (prometheus, grafana, loki, tempo)..."
    cd ./HyperCode-V2.4
    docker compose -f docker-compose.observability.yml up -d --pull always
    cd ..
    
    sleep 10
    log_info "Prometheus → http://localhost:9090"
    log_info "Grafana → http://localhost:3001"
    log_info "Loki → http://localhost:3100"
    log_info "Tempo → http://localhost:3200"
    echo ""
}

# Start agents
start_agents() {
    log_info "Starting agents (crew-orchestrator, coder, frontend-specialist, etc.)..."
    cd ./HyperCode-V2.4
    docker compose --profile agents up -d --pull always
    cd ..
    
    sleep 15
    log_info "Crew Orchestrator → http://localhost:8081"
    log_info "Coder Agent → http://localhost:8002"
    log_info "MCP Gateway → http://localhost:8820"
    echo ""
}

# Start health monitoring
start_health() {
    log_info "Starting health monitoring (hyperhealth, security-scanner, auto-prune)..."
    cd ./HyperCode-V2.4
    docker compose --profile health up -d --pull always
    cd ..
    
    sleep 10
    log_info "HyperHealth API → http://localhost:8095"
    echo ""
}

# Status check
show_status() {
    echo ""
    log_info "Service Status:"
    echo "==============="
    cd ./HyperCode-V2.4
    docker compose ps --all 2>/dev/null || echo "No services running"
    cd ..
    echo ""
}

# Menu
show_help() {
    echo "Usage: ./hypercode-quickstart.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  core        Start only core services (redis, postgres, hypercode-core, ollama)"
    echo "  agents      Start core + all agents (15+ AI agents)"
    echo "  health      Start core + health monitoring (security scanner, auto-prune)"
    echo "  full        Start core + observability + agents"
    echo "  all         Start everything (core + obs + agents + health + mission)"
    echo "  status      Show running services"
    echo "  stop        Stop all services"
    echo "  help        Show this message"
    echo ""
    echo "Examples:"
    echo "  ./hypercode-quickstart.sh core"
    echo "  ./hypercode-quickstart.sh full"
    echo "  ./hypercode-quickstart.sh all"
    echo ""
}

# Execute
case "$COMMAND" in
    core)
        create_networks
        create_data_dirs
        check_env
        start_core
        show_status
        ;;
    agents)
        create_networks
        create_data_dirs
        check_env
        start_core
        start_agents
        show_status
        ;;
    health)
        create_networks
        create_data_dirs
        check_env
        start_core
        start_health
        show_status
        ;;
    full)
        create_networks
        create_data_dirs
        check_env
        start_core
        start_observability
        start_agents
        show_status
        ;;
    all)
        create_networks
        create_data_dirs
        check_env
        start_core
        start_observability
        start_agents
        start_health
        log_info "Starting mission control..."
        cd ./HyperCode-V2.4
        docker compose --profile mission up -d --pull always 2>/dev/null || log_warn "Mission control skipped"
        cd ..
        show_status
        ;;
    status)
        cd ./HyperCode-V2.4
        docker compose ps --all
        cd ..
        ;;
    stop)
        log_info "Stopping all services..."
        cd ./HyperCode-V2.4
        docker compose down
        cd ..
        log_info "Services stopped"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

log_info "Done!"
