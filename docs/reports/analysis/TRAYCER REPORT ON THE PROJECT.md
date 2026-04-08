🧠 HyperCode V2.0 — Full Project Health Check & Understanding
🎯 What Is This Project?
HyperCode V2.0 is a neurodivergent-first AI agent platform — a "Cognitive Architecture" built specifically for people with dyslexia, ADHD, and autism. The core philosophy: "You do not just write code; you craft cognitive architectures."

It revolves around "BROski" — an AI partner concept — and Agent X, a meta-architect system that creates, deploys, and orchestrates specialized AI agents. The goal is to make coding and creating feel natural, guided, and judgment-free.

🏗️ Architecture Overview
👤 User / Browser

🌐 Nginx Gateway\n(80/443)

🖥️ Broski Terminal\nNext.js (3000)

✏️ HyperFlow Editor\nVite/React (5173)

📊 Dashboard\nNginx (8088)

⚙️ HyperCode Core\nFastAPI (8000)

⚙️ Celery Worker\nBackground Tasks

🎯 Crew Orchestrator\nFastAPI (8080)

🤖 8 Specialist Agents\n(8001–8008)

💻 Coder Agent (8001)

📦 Hyper-Agents-Box (5000)

🔌 MCP Server

🔴 Redis (6379)

🐘 PostgreSQL (5432)

🦙 Ollama LLM (11434)

📈 Prometheus (9090)

📊 Grafana (3001)

🔍 Jaeger (16686)

🚨 AlertManager (9093)

📦 Full Component Inventory
Core Platform (6 services)
Service	Tech	Port	Purpose
hypercode-core	Python / FastAPI	8000	Main API engine, HyperCode language runtime
broski-terminal	Next.js	3000	Primary user-facing terminal UI
hyperflow-editor	Vite / React	5173	Visual flow/code editor
crew-orchestrator	Python / FastAPI	8080	Agent coordination & task routing
hypercode-dashboard	Nginx (static HTML)	8088	Agent status dashboard
hypercode-nginx	Nginx	80/443	Reverse proxy / SSL gateway
celery-worker	Python / Celery	—	Background task queue (broker: Redis)
8 Specialist AI Agents (Python, PERPLEXITY Claude)
Agent	Port	Model	Role
project-strategist	8001	Claude Opus	Planning & delegation
frontend-specialist	8002	Claude Sonnet	UI/UX development
backend-specialist	8003	Claude Sonnet	API & business logic
database-architect	8004	Claude Sonnet	Schema & queries
qa-engineer	8005	Claude Sonnet	Testing & validation
devops-engineer	8006	Claude Sonnet	CI/CD & infrastructure
security-engineer	8007	Claude Sonnet	Security audits
system-architect	8008	Claude Opus	Architecture design
Additional Agents
Service	Port	Purpose
coder-agent	8001	Code execution (Docker socket access)
mcp-server	—	MCP protocol server (tool integration)
hyper-agents-box	5000	Agent management & orchestration box
Infrastructure
Service	Port	Purpose
redis	6379	Cache + Celery broker
postgres	5432	Primary database
ollama (tinyllama)	11434	Local LLM inference
Observability Stack
Service	Port	Purpose
prometheus	9090	Metrics scraping
grafana	3001	Dashboards
jaeger	16686	Distributed tracing
alertmanager	9093	Alert routing
node-exporter	9100	Host metrics
cadvisor	8080	Container metrics
🗂️ Sub-Projects (Satellite Platforms)
Sub-Project	Location	Tech	Purpose
HyperStudio	HyperStudio platform/	Python, FastAPI	AI video generation platform
Hyper Mission System	hyper-mission-system/	Node.js/Express + Vite/React + PostgreSQL	Mission/task tracking system
HyperFocus Zone Support Hub	hyperfocus Zone Support-Hub--main/	HTML/JS/CSS PWA	Support hub web app (service worker)
CLI	cli/	Python	Command-line interface tool
Hyper-Agents-Box	Hyper-Agents-Box/	Python	Agent management box
BROski Business Agents	BROski Business Agents/	Node.js (Next.js)	Business-focused agent tools
🧪 Testing Coverage
Test Type	Location	Tech
Unit / Integration	tests/test_agent_crew.py, tests/run_tests.py	Python / pytest
Functional	tests/functional/test_coder_capabilities.py	Python
End-to-End	tests/go-e2e/roundtrip_test.go	Go
Load / Performance	tests/load/locustfile.py, tests/load/swarm_load_test.js	Locust, k6
Custom Framework	tests/framework/	Python (runner, evaluator, scenarios)
Verification	verification/test_coder_agent_protocol.py	Python
Reported coverage: 80%+ (pytest suite)

🔑 Key Configuration Files
File	Purpose
Main production stack (33+ services)
Development overrides
Environment variable template
Prometheus scrape config
Alert routing rules
Prometheus alert rules
MCP server tool config
Hive Mind shared knowledge (Team Memory, Skills Library)
Kubernetes manifests for production scaling
Nginx reverse proxy config
Grafana dashboards, Prometheus rules, AlertManager config
🟢 Current Health Status (Feb 2026)
Overall: 🟢 98–100% Operational — Go-live validated on 2026-02-12.

Layer	Status	Notes
Core Platform	✅ 100% Healthy	All 6 services running
Agent Swarm (8/8)	✅ 100% Running	All health checks passing
Infrastructure	✅ 100% Healthy	Redis, Postgres, Ollama, Celery all healthy
Observability	✅ 100% Running	Prometheus, Grafana, Jaeger, AlertManager all active
coder-agent	⚠️ Probe failing	curl not in container PATH — service itself works fine
Resource usage (healthy):

Memory: ~2GB / 8GB (25%)
CPU: <1% average
Storage: ~17GB (9GB Ollama models, 6.8GB images, 500MB DB)
Volumes: 46 persistent volumes
⚠️ Known Issues & Remaining Risks
🔴 Minor (1 active)
Issue	Location	Impact	Fix
coder-agent healthcheck fails	agents/coder/Dockerfile	Docker shows "unhealthy" — service works	Replace curl with wget or Python in HEALTHCHECK
🟡 Security Risks (Defaults not changed)
Risk	Location	Action Needed
Weak DB password default	
 → POSTGRES_PASSWORD=changeme	Set strong 32+ char password in .env
Grafana default credentials	docker-compose.yml → admin/admin	Change via GF_SECURITY_ADMIN_PASSWORD in .env
JWT/API key placeholders	
Replace all your_*_here values
🟡 Structural Issues
Issue	Impact
Inconsistent profiles: ["agents"] tags	Some agents (frontend-specialist, security-engineer, system-architect) start without --profile agents, others don't — inconsistent startup behavior
Duplicate deploy: blocks in docker-compose.yml	crew-orchestrator and frontend-specialist have two deploy: keys — Docker Compose uses the last one, silently ignoring the first
Sub-projects have their own docker-compose.yml files	HyperStudio platform/, hyper-mission-system/, scripts/ each have separate compose files — not integrated into the main stack
Nested project structure	Deep paths like ./THE HYPERCODE/hypercode-core cause confusion
🚀 How to Start the Full Stack
bash

# 1. Configure environment
cp .env.example .env
# Edit .env — fill in API keys, strong passwords
# 2. Start core stack
docker compose up -d
# 3. Start agent swarm (requires --profile agents)
docker compose --profile agents up -d
# 4. Verify health
docker compose ps
Access Points:

Interface	URL
Broski Terminal (UI)	http://localhost:3000
HyperFlow Editor	http://localhost:5173
HyperCode API	http://localhost:8000
Crew Orchestrator	http://localhost:8080
Dashboard	http://localhost:8088
Grafana	http://localhost:3001
Prometheus	http://localhost:9090
Jaeger Tracing	http://localhost:16686
Ollama LLM	http://localhost:11434
📋 Priority Action List
Priority	Action	Time
🔴 Fix now	Change all default passwords in .env (Postgres, Grafana, JWT, API key)	20 min
🔴 Fix now	Fix coder-agent Dockerfile healthcheck (replace curl with wget)	5 min
🟡 This week	Fix duplicate deploy: blocks in 
 for crew-orchestrator and frontend-specialist	15 min
🟡 This week	Standardize profiles: ["agents"] across all 8 specialist agents in 
10 min
🟢 Next sprint	Integrate sub-project compose files (HyperStudio, hyper-mission-system) into main stack or document them separately	1–2 hrs
🟢 Next sprint	Add API gateway (rate limiting, auth) in front of agent ports	2–4 hrs
🧬 Tech Stack Summary
Layer	Technology
Backend	Python 3.11, FastAPI, Celery
Frontend	Next.js (React), Vite/React
Database	PostgreSQL 15, Redis 7
AI / LLM	PERPLEXITY Claude (Opus + Sonnet), Ollama (tinyllama local)
Containerization	Docker, Docker Compose, Kubernetes (k8s/)
Monitoring	Prometheus, Grafana, Jaeger, AlertManager, cAdvisor, node-exporter
CI/CD	GitHub Actions (.github/), Husky + commitlint (conventional commits)
Node.js	openai SDK v6, commitlint, husky
Security	no-new-privileges, cap_drop: ALL, AES-GCM encryption, API key auth, network isolation
