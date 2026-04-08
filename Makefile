# Makefile for HyperCode Agent Crew
# Simplifies common Docker operations

.PHONY: help build up down logs status clean test restart network-init init start agents stop setup dev prod scan scan-quick scan-sast scan-secrets scan-deps scan-iac scan-licenses scan-report pre-commit-install

# Default target
help:
	@echo "HyperCode Agent Crew - Available Commands:"
	@echo "  make build        - Build all agent containers"
	@echo "  make up           - Start all agents"
	@echo "  make down         - Stop all agents"
	@echo "  make restart      - Restart all agents"
	@echo "  make logs         - View logs (all agents)"
	@echo "  make status       - Check agent status"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make test         - Test orchestrator API"
	@echo "  make network-init - Ensure hypercode_public_net exists"
	@echo ""
	@echo "Scanning & Quality Gates:"
	@echo "  make scan              - Full local scan suite"
	@echo "  make scan-quick        - SAST + secrets only (fast)"
	@echo "  make scan-sast         - Bandit + Ruff + Semgrep"
	@echo "  make scan-secrets      - detect-secrets + Gitleaks"
	@echo "  make scan-deps         - pip-audit + npm audit"
	@echo "  make scan-iac          - Hadolint + Trivy IaC + compose validate"
	@echo "  make scan-licenses     - License compliance audit"
	@echo "  make scan-report       - Regenerate HTML dashboard"
	@echo "  make pre-commit-install - Install pre-commit hooks (once)"
	@echo ""
	@echo "Individual agent commands:"
	@echo "  make logs-frontend    - View frontend specialist logs"
	@echo "  make logs-backend     - View backend specialist logs"
	@echo "  make restart-frontend - Restart frontend specialist"

# Ensure shared public network exists
network-init:
	@echo "Ensuring Docker network 'hypercode_public_net' exists..."
	@docker network ls --format '{{.Name}}' | grep -q '^hypercode_public_net$$' || docker network create hypercode_public_net

# Build all containers
build: network-init
	@echo "Building all agent containers..."
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents build

# Start all agents
up: network-init
	@echo "Starting all agents..."
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents up -d
	@echo "✅ Agents started!"
	@echo "🌐 Orchestrator: http://localhost:8080"
	@echo "📊 Dashboard: http://localhost:8090"

# Stop all agents
down:
	@echo "Stopping all agents..."
	docker-compose -f docker-compose.yml --profile agents down

# Restart all agents
restart: down up

# View logs (all agents)
logs:
	docker-compose -f docker-compose.yml --profile agents logs -f

# View specific agent logs
logs-orchestrator:
	docker-compose -f docker-compose.yml --profile agents logs -f crew-orchestrator

logs-strategist:
	docker-compose -f docker-compose.yml --profile agents logs -f project-strategist

logs-frontend:
	docker-compose -f docker-compose.yml --profile agents logs -f frontend-specialist

logs-backend:
	docker-compose -f docker-compose.yml --profile agents logs -f backend-specialist

logs-database:
	docker-compose -f docker-compose.yml --profile agents logs -f database-architect

logs-qa:
	docker-compose -f docker-compose.yml --profile agents logs -f qa-engineer

logs-devops:
	docker-compose -f docker-compose.yml --profile agents logs -f devops-engineer

logs-security:
	docker-compose -f docker-compose.yml --profile agents logs -f security-engineer

logs-architect:
	docker-compose -f docker-compose.yml --profile agents logs -f system-architect

# Restart specific agent
restart-frontend:
	docker-compose -f docker-compose.yml --profile agents restart frontend-specialist

restart-backend:
	docker-compose -f docker-compose.yml --profile agents restart backend-specialist

restart-strategist:
	docker-compose -f docker-compose.yml --profile agents restart project-strategist

# Check agent status
status:
	@echo "Docker containers status:"
	@docker-compose -f docker-compose.yml --profile agents ps
	@echo ""
	@echo "Querying orchestrator API..."
	@curl -s http://localhost:8080/agents/status 2>/dev/null | python3 -m json.tool || echo "Orchestrator not responding"

# Clean up everything
clean:
	@echo "⚠️  This will remove all containers, volumes, and images"
	@read -p "Continue? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose -f docker-compose.yml --profile agents down -v --remove-orphans
	docker system prune -f

# Full Docker Health Check System
full-docker-health:
	@echo "🚀 Starting Full Docker Health Check Pipeline..."
	@echo "1. Installing dependencies..."
	@pip install -q pyyaml requests
	@echo "2. Inventorying K8s manifests & Monitoring configs..."
	@python scripts/generate_health_check_compose.py
	@echo "3. Running Health Check Controller..."
	@python scripts/health_check_controller.py

# Test orchestrator API
test:
	@echo "Testing orchestrator health..."
	@curl -s http://localhost:8080/health | python3 -m json.tool
	@echo ""
	@echo "Testing agent status endpoint..."
	@curl -s http://localhost:8080/agents/status | python3 -m json.tool

# Initialize environment — create networks, data dirs, validate .env
init: ## First-time setup: create networks, data dirs, validate .env
	@echo "HyperCode V2.0 — Init"
	@powershell -File scripts/init.ps1 2>/dev/null || bash scripts/init.sh
	@echo "Init complete. Run 'make start' to launch."

# Start the full production stack
start: init ## Start the full production stack
	docker compose up -d

# Start only the agents stack
agents: init ## Start only the agents stack (standalone)
	docker compose -f docker-compose.agents.yml up -d --build

# Stop everything
stop: ## Stop all running stacks
	docker compose down
	docker compose -f docker-compose.agents.yml down

# Full setup (init + build + up)
setup: init build up
	@echo "🎉 Setup complete!"
	@echo "🌐 Orchestrator: http://localhost:8080"
	@echo "📊 Dashboard: http://localhost:8090"

# Development mode (with auto-reload)
dev:
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents up

# ── Scanning & Quality Gates ──────────────────────────────────────────────

scan: ## Run the full local scan suite (all categories)
	@echo "Running full scan suite..."
	@bash scripts/scan/run-all-scans.sh

scan-quick: ## Run SAST + secret detection only (fast, pre-push check)
	@bash scripts/scan/run-all-scans.sh --only sast
	@bash scripts/scan/run-all-scans.sh --only secrets

scan-sast: ## Run Bandit + Ruff + Semgrep static analysis
	@bash scripts/scan/run-all-scans.sh --only sast

scan-secrets: ## Run detect-secrets + Gitleaks
	@bash scripts/scan/run-all-scans.sh --only secrets

scan-deps: ## Run pip-audit + npm audit dependency CVE scan
	@bash scripts/scan/run-all-scans.sh --only deps

scan-iac: ## Run Hadolint + Trivy IaC + docker compose validation
	@bash scripts/scan/run-all-scans.sh --only iac

scan-licenses: ## Run license compliance audit (pip-licenses)
	@bash scripts/scan/run-all-scans.sh --only licenses

scan-report: ## Regenerate HTML dashboard from existing reports/
	@python3 scripts/scan/generate-dashboard.py \
		--reports-dir reports \
		--output reports/dashboard.html \
		--commit "$$(git rev-parse --short HEAD 2>/dev/null || echo local)" \
		--branch "$$(git branch --show-current 2>/dev/null || echo local)"
	@echo "Dashboard: reports/dashboard.html"

pre-commit-install: ## Install pre-commit hooks (run once per dev machine)
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Pre-commit hooks installed."

# Production mode
prod:
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents up -d --scale frontend-specialist=2 --scale backend-specialist=2
