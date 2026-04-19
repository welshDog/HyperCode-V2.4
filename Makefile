# Makefile for HyperCode Agent Crew
# Simplifies common Docker operations

.PHONY: help build up down logs status clean test restart network-init init start agents stop setup dev prod scan scan-quick scan-sast scan-secrets scan-deps scan-iac scan-licenses scan-report pre-commit-install scan-agent scan-all scan-build trivy-hook-install calm load-test load-test-headless load-test-k6 load-test-k6-smoke load-test-agents load-test-stripe-k6 load-test-all

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
	@echo "Trivy Image Scanning (Phase 8):"
	@echo "  make scan-agent AGENT=healer  - Scan one live agent image"
	@echo "  make scan-all                 - Scan entire fleet"
	@echo "  make scan-build AGENT=healer  - Build + scan from Dockerfile"
	@echo "  make trivy-hook-install       - Install pre-push CVE hook"
	@echo ""
	@echo "Individual agent commands:"
	@echo "  make logs-frontend    - View frontend specialist logs"
	@echo "  make logs-backend     - View backend specialist logs"
	@echo "  make restart-frontend - Restart frontend specialist"
	@echo ""
	@echo "Load Testing:"
	@echo "  make load-test-k6        - k6 API load test (target up to 1000 rps)"
	@echo "  make load-test-k6-smoke  - fast k6 smoke run"
	@echo "  make load-test-agents    - k6 agents status polling load test"
	@echo "  make load-test-stripe-k6 - k6 Stripe checkout load profile (test mode)"

# Ensure shared public network exists
network-init:
	@echo "Ensuring Docker network 'hypercode_public_net' exists..."
	@docker network ls --format '{{.Name}}' | grep -q '^hypercode_public_net$$' || docker network create hypercode_public_net

# Pre-build safety check (disk + memory guard)
pre-build-check:
	@bash scripts/pre-build-check.sh

# Build all containers
build: pre-build-check network-init
	@echo "Building all agent containers..."
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents build

# Start full stack with secrets
up:
	docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Stop full stack
down:
	docker compose -f docker-compose.secrets.yml down

# Restart full stack
restart:
	docker compose -f docker-compose.yml -f docker-compose.secrets.yml restart

# View logs (all services)
logs:
	docker compose -f docker-compose.yml -f docker-compose.secrets.yml logs -f

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

health: ## 🏥 NemoClaw code health scan + Discord webhook post
	@echo "🔍 Running NemoClaw health scan..."
	@python scripts/health_report.py --webhook

health-quick: ## 🏥 NemoClaw scan — terminal only, no webhook
	@python scripts/health_report.py

# Full Docker Health Check System
full-docker-health:
	@echo "🚀 Starting Full Docker Health Check Pipeline..."
	@echo "1. Installing dependencies..."
	@pip install -q pyyaml requests
	@echo "2. Inventorying K8s manifests & Monitoring configs..."
	@python scripts/generate_health_check_compose.py
	@echo "3. Running Health Check Controller..."
	@python scripts/health_check_controller.py

# Run the full pytest test suite
test:
	pytest backend/tests/ -v

calm:
	python scripts/pets/award_focus_session.py

# Run ruff linter
lint:
	ruff check .

# CI: lint + tests (what GitHub Actions runs)
ci: lint test
	@echo "✅ CI passed"

# Legacy: curl health checks against running stack
health-check:
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

# ── Trivy Image Security Scanning (Phase 8) ───────────────────────────────
# Requires: hyper-shield-scanner container running  OR  trivy installed locally

TRIVY_AGENTS := agent-x healer coder crew-orchestrator broski-bot \
  01-frontend-specialist 02-backend-specialist 03-database-architect \
  04-qa-engineer 05-devops-engineer 06-security-engineer \
  07-system-architect 08-project-strategist 09-tips-tricks-writer \
  throttle-agent coderabbit-webhook

# Scan a single agent image (running container via hyper-shield-scanner)
# Usage: make scan-agent AGENT=healer
scan-agent: ## Scan one agent image: make scan-agent AGENT=<name>
	@echo "🔍 Scanning hypercode-v24-$(AGENT)..."
	docker exec hyper-shield-scanner trivy image \
		--scanners vuln \
		--severity HIGH,CRITICAL \
		--quiet \
		hypercode-v24-$(AGENT)

# Scan all live agent images via hyper-shield-scanner
scan-all: ## Scan every agent image (uses running hyper-shield-scanner)
	@echo "🔒 HyperCode fleet scan — $(shell date -u)"
	@FAILED=0; \
	for agent in $(TRIVY_AGENTS); do \
	  echo "🔍 Scanning $$agent..."; \
	  docker exec hyper-shield-scanner trivy image \
	    --scanners vuln \
	    --severity HIGH,CRITICAL \
	    --format table \
	    --quiet \
	    hypercode-v24-$$agent || FAILED=1; \
	done; \
	if [ $$FAILED -eq 1 ]; then \
	  echo "🔴 Some images have CRITICAL/HIGH CVEs — see output above."; \
	  exit 1; \
	fi; \
	echo "✅ All images passed!"

# Build + scan a single agent from source (no running container needed)
# Usage: make scan-build AGENT=healer
scan-build: ## Build + scan from Dockerfile: make scan-build AGENT=<name>
	@echo "🔨 Building + scanning $(AGENT) from source..."
	docker build -f agents/$(AGENT)/Dockerfile -t hypercode-scan-$(AGENT):local . 2>&1 | tail -5
	trivy image \
		--scanners vuln \
		--severity HIGH,CRITICAL \
		--format table \
		hypercode-scan-$(AGENT):local
	@docker rmi hypercode-scan-$(AGENT):local 2>/dev/null || true

# Install the Trivy pre-push git hook
trivy-hook-install: ## Install Trivy pre-push hook for local CVE blocking
	cp scripts/trivy-pre-push.sh .git/hooks/pre-push
	chmod +x .git/hooks/pre-push
	@echo "✅ Trivy pre-push hook installed."

## ─── Load Testing ──────────────────────────────────────────────────────────

load-test: ## Launch Locust web UI — open http://localhost:8089
	@echo "🚀 Starting Locust load test UI at http://localhost:8089"
	@echo "   Target: http://localhost:8000"
	@pip install locust --break-system-packages --quiet 2>/dev/null || true
	locust -f tests/load/locustfile.py --host http://localhost:8000

load-test-headless: ## Run headless load test: 50 users, 10/s ramp, 2 min, HTML report
	@echo "🏴󠁧󠁢󠁷󠁬󠁳󠁠 Running headless load test (50u, 10/s ramp, 2min)..."
	@pip install locust --break-system-packages --quiet 2>/dev/null || true
	locust -f tests/load/locustfile.py \
		--host http://localhost:8000 \
		--headless \
		-u 50 -r 10 \
		--run-time 2m \
		--html tests/load/report.html
	@echo "📊 Report saved to tests/load/report.html"

load-test-k6: ## k6 main API test (target up to 1000 req/sec profile)
	@echo "🔥 Running k6 main load profile: tests/load/hypercode_load_test.js"
	@docker run --rm -i -e BASE_URL=$${BASE_URL:-http://host.docker.internal:8000} grafana/k6 run - < tests/load/hypercode_load_test.js

load-test-k6-smoke: ## k6 quick smoke check (10 VUs, 30s)
	@echo "⚡ Running k6 smoke profile (10 VUs, 30s)"
	@docker run --rm -i -e BASE_URL=$${BASE_URL:-http://host.docker.internal:8000} grafana/k6 run \
		--vus 10 --duration 30s - < tests/load/hypercode_load_test.js

load-test-agents: ## k6 agent status endpoint load test
	@echo "🤖 Running k6 agent status load profile"
	@docker run --rm -i -e BASE_URL=$${BASE_URL:-http://host.docker.internal:8000} grafana/k6 run - < tests/load/agents_load_test.js

load-test-stripe-k6: ## k6 Stripe checkout flow load test (test mode keys only)
	@echo "💳 Running k6 Stripe load profile (test mode only)"
	@docker run --rm -i -e BASE_URL=$${BASE_URL:-http://host.docker.internal:8000} grafana/k6 run - < tests/load/stripe_load_test.js

load-test-all: load-test-k6-smoke load-test-k6 load-test-agents load-test-stripe-k6 ## Run every k6 profile sequentially (smoke → main → agents → stripe)
	@echo "✅ All k6 load profiles complete — thresholds: P99<100ms, err<0.1%, target 1000 rps"

## ─── Production ─────────────────────────────────────────────────────────────

# Production mode
prod:
	docker-compose -f docker-compose.yml --profile agents --env-file .env.agents up -d --scale frontend-specialist=2 --scale backend-specialist=2
