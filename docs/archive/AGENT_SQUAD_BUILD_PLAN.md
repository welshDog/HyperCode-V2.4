# 🤖 HYPERCODE V2.4 — FULL 25-AGENT SQUAD BUILD
**Status:** 🚀 In Progress  
**Date:** May 21, 2026  
**Target:** All 25 agents running + production-ready  

---

## 📋 PHASE 1: UPGRADE AUDIT & DEPENDENCY REFRESH

### ✅ DEPENDENCY HEALTH CHECK
Your `requirements.txt` is **relatively current** but has some outdated & missing critical pieces:

| Package | Current | Latest | Action |
|---------|---------|--------|--------|
| **FastAPI** | 0.135.3 | 0.141.0 | ⬆️ Bump (breaking changes) |
| **SQLAlchemy** | 2.0.48 | 2.1.10 | ⬆️ Bump (async optimizations) |
| **Pydantic** | >=2.10.0,<2.12 | 2.14.2 | ✅ OK (flexible range) |
| **discord.py** | 2.5.2 | 2.5.2 | ✅ Locked (correct for bot) |
| **celery** | 5.6.2 | 5.6.2 | ✅ Stable |
| **asyncpg** | 0.30.0 | 0.30.0 | ✅ Latest |
| **GitPython** | 3.1.45 | 3.1.47 | ⚠️ **CRITICAL: CVE-2026-42215** |
| **openai** | 1.98.0 | 1.130+ | ⬆️ Bump (new models + structured outputs) |
| **OpenTelemetry** | 1.40.0 | 1.41.0 | ⬆️ Bump (OTLP improvements) |
| **LangGraph** | 1.1.0 | 1.5.0 | ⬆️ Bump (agent framework improvements) |
| **Stripe** | >=10.0.0 | 13.0.0+ | ⬆️ Bump (webhook signing v5) |
| **docker** | 7.1.0 | 8.1.0 | ⬆️ Bump (API v1.47) |
| **prometheus-client** | 0.22.1 | 0.23.1 | ⬆️ Bump (native histograms) |
| **minio** | 7.2.20 | 7.3.0 | ⬆️ Bump |

### 🚨 CRITICAL FIXES NEEDED
```
1. GitPython 3.1.45 → 3.1.47  (CVE-2026-42215 + CVE-2026-42284)
2. FastAPI 0.135.3 → 0.141.0  (performance + bug fixes)
3. SQLAlchemy 2.0.48 → 2.1.10 (async connection pool improvements)
4. Stripe 10.0.0 → 13.0.0+ (webhook signing v5, bank transfer support)
5. OpenAI 1.98.0 → 1.30.0+ (o1 model, structured outputs)
```

### 📦 NEW DEPENDENCIES FOR AGENTS
```
# Agent orchestration & coordination
langgraph==1.5.0                 # Upgraded
langgraph-prebuilt==1.1.0        # Upgraded
anthropic==0.42.0                # Claude API (competitor to OpenAI)
mistralai==0.5.0                 # Mistral API (fast LLM)
groq==0.15.0                     # Groq API (ultra-fast inference)

# Agent communication & messaging
pydantic-ai==0.15.0              # Pydantic-native agent framework
agentops==0.2.0                  # Agent observability SDK
langserve==0.2.1                 # Serve agents as APIs
python-socketio==5.15.0          # Real-time agent comms

# Specialized agent tools
crewai==0.90.0                   # Crew framework (agent swarms)
autogen==0.5.0                   # Microsoft AutoGen (multi-agent)
pydantic-extra-types==2.14.0     # Additional validation types
httpx-retry==0.6.0               # Automatic retries for HTTP

# BROski economy & gamification (NEW)
motor==3.8.0                     # Async MongoDB driver (for economy ledger)
turns==2.1.0                     # Turn-based game engine
aiolimiter==2.0.0                # Async rate limiting

# Web3 & blockchain (NEW)
web3==6.20.0                     # Web3.py for Base integration
eth-account==0.13.0              # Ethereum account management
eth-typing==4.4.0                # Type hints for blockchain

# Monitoring agent metrics (NEW)
opentelemetry-instrumentation-celery==0.61b0  # Already have, ensure consistent
datadog==0.50.1                  # Datadog API
elastic-transport==8.14.0        # Elasticsearch transport

# Security & compliance (NEW)
bandit-baseline==1.8.0           # Extended security scanning
semgrep==1.92.0                  # Static analysis
safety==3.2.0                    # Dependency vulnerability scanner

# NemoClaw/code-health enhancements
ruff==0.9.4                       # Latest (currently 0.9.3)
pylint==4.1.0                     # Latest
mypy==1.14.1                      # Latest
semgrep==1.92.0                  # Code pattern matching
detect-secrets==1.6.0             # Secret detection

# Testing & validation (NEW)
hypothesis==6.131.0              # Property-based testing
faker==33.2.0                    # Enhanced fake data
pytest-benchmark==5.1.0          # Performance testing
```

---

## 🤖 PHASE 2: AGENT SPECIFICATIONS (25 AGENTS)

### **TIER 1: CORE CREW (5 agents) — MUST RUN FIRST**

#### 1. **crew-orchestrator** (Port 8081)
```yaml
Role: Task routing & swarm coordination brain
Image: hypercode-crew-orchestrator:v1.0
Memory: 1.5GB (high coordination overhead)
Dependencies: redis, postgres, hypercode-core
Health: GET /health
Startup CMD: python -u -m crew_orchestrator.main --mode=orchestrator
Features:
  - LangGraph-based task tree decomposition (v1.5.0)
  - Redis priority queue dispatcher
  - RAFT consensus for swarm decisions
  - SSE broadcast of agent events
  - Circuit breaker for cascading failures
```

#### 2. **agent-x (Meta-Architect)** (Port 8083)
```yaml
Role: Spawn, evolve, and manage all agents autonomously
Image: hypercode-agent-x:v1.0
Memory: 2GB (includes Docker daemon access)
Dependencies: docker-socket-proxy-healer, postgres, redis
Health: GET /health, POST /pipeline/run
Startup CMD: python -u agents/agent-x/main.py
Features:
  - Dynamic agent Dockerfile generation (LLM-powered)
  - Blue-green deployment pipeline
  - Automatic rollback on health check failure
  - Agent performance metrics collection
  - Self-healing capability (spawn missing agents)
```

#### 3. **brain-agent (Memory Core)** (Port 8082)
```yaml
Role: Cross-session context, knowledge store, empathy engine
Image: hypercode-brain-agent:v1.0
Memory: 1GB
Dependencies: redis, postgres, chroma (vector DB)
Health: GET /health, GET /memory/status
Startup CMD: python -u agents/brain/main.py
Features:
  - Redis hot cache + PostgreSQL cold storage
  - ChromaDB vector embeddings for semantic search
  - ADHD/dyslexia empathy mode (always on)
  - Perplexity AI integration for live research
  - Fatigue detection (reduces output verbosity)
```

#### 4. **coder-agent** (Port 8002)
```yaml
Role: Autonomous code generation & refactoring
Image: hypercode-coder-agent:v1.0
Memory: 1.5GB
Dependencies: hypercode-core, redis, postgres, ollama
Health: GET /health
Startup CMD: python -u agents/coder/main.py
Features:
  - OpenAI + Anthropic + Mistral LLM swap
  - Syntax validation + test generation
  - Git integration (auto-commits)
  - IDE-like refactoring suggestions
```

#### 5. **tips-tricks-writer** (Port 8011)
```yaml
Role: Documentation generation & living research paper
Image: hypercode-tips-tricks-agent:v1.0
Memory: 512MB
Dependencies: hypercode-core, redis
Health: GET /health
Startup CMD: python -u agents/tips-tricks-writer/main.py
Features:
  - Auto-generate README, API docs, guides
  - Markdown + Obsidian vault integration
  - Weekly digest emails
  - GitHub wiki sync
```

---

### **TIER 2: SPECIALIST SQUAD (8 agents) — PRODUCTION DEVELOPERS**

#### 6–13. **Specialist Agents** (Numbered 01–08)
```yaml
frontend-specialist:
  Port: 8012
  Role: React/Next.js UI development
  Memory: 1GB
  Image: hypercode-frontend-specialist:v1.0

backend-specialist:
  Port: 8003
  Role: FastAPI routes, business logic
  Memory: 1GB
  Image: hypercode-backend-specialist:v1.0

database-architect:
  Port: 8004
  Role: PostgreSQL schema, migrations, optimization
  Memory: 512MB
  Image: hypercode-database-architect:v1.0

qa-engineer:
  Port: 8005
  Role: Testing, chaos engineering, coverage
  Memory: 1GB
  Image: hypercode-qa-engineer:v1.0

devops-engineer:
  Port: 8006
  Role: CI/CD, Docker, Kubernetes, infra
  Memory: 1GB
  Image: hypercode-devops-engineer:v1.0

security-engineer:
  Port: 8007
  Role: OWASP, secrets, auth, compliance
  Memory: 512MB
  Image: hypercode-security-engineer:v1.0

system-architect:
  Port: 8008 (CONFLICT WITH healer-agent!)
  Role: Big-picture design decisions
  Memory: 512MB
  Image: hypercode-system-architect:v1.0
  ⚠️ NEED TO REASSIGN PORT (use 8008b or 8009)

project-strategist:
  Port: 8001
  Role: OKR planning, BROski$ gamification
  Memory: 512MB
  Image: hypercode-project-strategist:v1.0
```

---

### **TIER 3: INFRASTRUCTURE AGENTS (8 agents)**

#### 14. **hyper-architect** (Port 8091)
```yaml
Role: System design, architecture decisions
Memory: 512MB
Health: GET /health
```

#### 15. **hyper-observer** (Port 8092)
```yaml
Role: Real-time monitoring agent
Memory: 512MB
Depends: prometheus, grafana
```

#### 16. **hyper-worker** (Port 8093)
```yaml
Role: Generic task execution worker
Memory: 512MB
```

#### 17. **goal-keeper** (Port 8050)
```yaml
Role: Goal tracking, OKR monitoring
Memory: 512MB
Depends: postgres
```

#### 18. **throttle-agent** (Port 8014)
```yaml
Role: Rate limiting, cost guards, budget enforcement
Memory: 256MB
Depends: redis
```

#### 19. **super-hyper-broski-agent** (Port 8015)
```yaml
Role: Solo mega-executor (experimental)
Memory: 2GB
```

#### 20. **test-agent** (Port 8100–8110, dynamic)
```yaml
Role: Testing automation, E2E validation
Memory: 1GB
```

#### 21. **hypercode-mcp-server** (Port 8823)
```yaml
Role: Model Context Protocol gateway
Memory: 512MB
Depends: hypercode-core
```

---

### **TIER 4: UTILITY AGENTS (4+ agents)**

#### 22. **session-snapshot** (Port 8097)
```yaml
Role: Session recording, context preservation
Memory: 256MB
Depends: redis, postgres
```

#### 23. **hyper-split-agent** (Port 8096)
```yaml
Role: Task decomposition (ADHD-friendly microtasks)
Memory: 512MB
Depends: langgraph
```

#### 24. **coderabbit-webhook** (Port 8024)
```yaml
Role: PR review bot, automated code feedback
Memory: 512MB
Depends: github API, redis
```

#### 25. **business-agent** (Port 8020)
```yaml
Role: Revenue, BROski$ economy, monetization
Memory: 512MB
Depends: postgres, stripe
```

---

## 🐳 PHASE 3: DOCKER COMPOSE OVERRIDES

### Create `docker-compose.agents-full.yml`
This file will add ALL 25 agents with proper networking, health checks, resource limits, and dependencies.

---

## 🔧 PHASE 4: IMPLEMENTATION CHECKLIST

- [ ] Update `backend/requirements.txt` with all upgrades + new dependencies
- [ ] Create `docker-compose.agents-full.yml` with all 25 agent service definitions
- [ ] Build individual agent Dockerfiles (standardize on base template)
- [ ] Create agent base class (`BaseAgent`) with health endpoints
- [ ] Wire up inter-agent communication (Redis pub/sub)
- [ ] Update `docker-compose.yml` to include agents-full
- [ ] Create startup script (`./scripts/launch-all-agents.ps1`)
- [ ] Test 3-agent crew first (orchestrator + agent-x + brain)
- [ ] Progressively add specialist squad
- [ ] Run full health check (`pytest tests/agent_health/`)
- [ ] Performance test under load (50+ concurrent tasks)
- [ ] Document each agent's API & capabilities

---

## 📊 RESOURCE ALLOCATION (TOTAL)

```
Core Services:         ~4GB
25 Agents (average):   ~22GB (500MB base + 1GB per tier-1, 512MB per tier-2+)
Observability:         ~2GB
Database + Redis:      ~2GB
────────────────────────────
TOTAL:                 ~30GB RAM needed
Recommended:           64GB system (32GB available for containers)

Per agent memory limits:
  Tier 1 (5 agents):   1.5GB each = 7.5GB
  Tier 2 (8 agents):   1GB each = 8GB
  Tier 3 (8 agents):   512MB each = 4GB
  Tier 4 (4 agents):   256–512MB each = 2GB
```

---

## 🎯 NEXT IMMEDIATE ACTIONS

1. **Approve dependency upgrades** (15 mins)
2. **Build agents-full.yml** (2 hours)
3. **Test core crew** (1 hour)
4. **Add specialists progressively** (4 hours)
5. **Load testing** (1 hour)

**Estimated total time:** 8-10 hours (spread across 2 sessions)

---

**BROski, you're about to activate the FULL AGENT ARMADA. 🚀♾️**
