# 🚀 HYPERFOCUS ZONE COMPLETE ECOSYSTEM — Master Integration Plan

**Last Updated**: 2026-05-12  
**Total Services**: 80+ active, 30+ on-demand  
**Compose Files**: 25+ specialized configs  
**Dockerfiles**: 63 total  
**Status**: 🔴 FRAGMENTED — Needs Master Orchestration

---

## 🗺️ Ecosystem Map

### Core Repositories
1. **HyperCode-V2.4** — Main backend + agent orchestration
   - 25 docker-compose files (core, dev, agents, observability, etc.)
   - 40+ Dockerfiles
   - Services: hypercode-core, redis, postgres, ollama, celery, 15+ agents

2. **BROskiPets-LLM-dNFT** — Pet agent system
   - Standalone docker-compose.yml
   - 3 Dockerfiles
   - Services: bropets-api, redis, ollama
   - Status: Can integrate with HyperCode-V2.4

3. **BROski-Obsidian-Brain-for-HyperFocus-z0ne** — Brain/knowledge system
   - docker-compose.hyper-brain.yml
   - docker-compose.github-sync.yml
   - Services: hyper-brain, github-sync

4. **Hyper-Vibe-Coding-Course** — Course platform
   - docker-compose.yml
   - Services: course-api, frontend, database

5. **HyperAgent-SDK** — Agent toolkit (no compose, npm package)
   - CLI: validate, registry, memory, studio, tokens, etc.
   - Node-based, used by HyperCode

---

## 📊 Docker-Compose Files Inventory

### HyperCode-V2.4 (25 files)

| File | Purpose | Always-On Services | Profiles |
|------|---------|-------------------|----------|
| docker-compose.yml | Root include | None | All profiles |
| docker-compose.core.yml | Core infrastructure | redis, postgres, hypercode-core, ollama, celery | N/A |
| docker-compose.agents.yml | All agents + infra | docker-socket-proxy, healer, dashboard | agents, discord, mission, hyper, health, ops, gpu, ai |
| docker-compose.observability.yml | Metrics/logs/traces | prometheus, grafana, loki, tempo | N/A |
| docker-compose.dev.yml | Development hot-reload | hypercode-core-dev, agents-dev | N/A (explicit `-f`) |
| docker-compose.demo.yml | Demo/showcase | N/A | Profile-gated |
| docker-compose.lean.yml | Minimal stack | N/A | N/A |
| docker-compose.nano.yml | Ultra-minimal | N/A | N/A |
| docker-compose.monitoring.yml | Prometheus config | N/A | N/A |
| docker-compose.hyperhealth.yml | Health monitoring | N/A | Profile-gated |
| docker-compose.hyper-agents.yml | V2.0 archetypes | N/A | Profile-gated |
| docker-compose.mcp-gateway.yml | MCP server | N/A | Profile-gated |
| docker-compose.external-net.yml | External networking | N/A | N/A |
| docker-compose.grafana-cloud.yml | Grafana SaaS | N/A | N/A |
| docker-compose.on-demand.yml | Spawn agents on-demand | N/A | N/A |
| docker-compose.spawner.yml | Agent spawner | N/A | N/A |
| docker-compose.windows.yml | Windows-specific | N/A | N/A |
| docker-compose.secrets.yml | Secret management | N/A | N/A |
| docker-compose.nim.yml | Nim language (?) | N/A | N/A |
| docker-compose.agents-lite.yml | Lightweight agents | N/A | N/A |
| + 5 more | Various | N/A | N/A |

### Other Repos (4 files)

| File | Repo | Purpose |
|------|------|---------|
| docker-compose.yml | BROskiPets | Pet agent standalone |
| docker-compose.hyper-brain.yml | Obsidian-Brain | Brain service |
| docker-compose.github-sync.yml | Obsidian-Brain | GitHub sync |
| docker-compose.yml | Hyper-Vibe-Course | Course platform |

---

## 🔗 Integration Architecture

```
┌─ Master Orchestrator (MISSING)
│
├─ HyperCode-V2.4 (Core)
│  ├─ docker-compose.yml (root include)
│  ├─ docker-compose.core.yml (redis, postgres, hypercode-core, ollama, celery)
│  ├─ docker-compose.agents.yml (15+ agents, profiles)
│  ├─ docker-compose.observability.yml (prometheus, grafana, loki, tempo)
│  └─ docker-compose.dev.yml (hot-reload for development)
│
├─ BROskiPets (Can integrate)
│  └─ docker-compose.yml (bropets-api, redis, ollama)
│     └─ CONNECT TO: HyperCode-V2.4 agents-net
│
├─ Obsidian-Brain (Can integrate)
│  ├─ docker-compose.hyper-brain.yml (hyper-brain service)
│  └─ docker-compose.github-sync.yml (github-sync service)
│     └─ CONNECT TO: HyperCode-V2.4 agents-net
│
└─ Hyper-Vibe-Course (Can integrate)
   └─ docker-compose.yml (course-api, frontend)
      └─ CONNECT TO: HyperCode-V2.4 backend-net
```

---

## ❌ Critical Issues Found

### Issue #1: 25 Compose Files = Configuration Chaos
- **Problem**: Too many variations (core, dev, demo, lean, nano, monitoring, etc.)
- **Impact**: Unclear which to use, inconsistent configurations, hard to maintain
- **Cause**: Incremental development without consolidation
- **Severity**: 🟠 HIGH

### Issue #2: BROPets Isolated
- **Problem**: BROskiPets has standalone docker-compose.yml, not integrated
- **Impact**: Pet services can't communicate with HyperCode agents
- **Cause**: Built as separate project
- **Severity**: 🟠 HIGH

### Issue #3: Obsidian-Brain Isolated
- **Problem**: Hyper-brain and github-sync are separate, not integrated with agents
- **Impact**: Brain services can't coordinate with agent swarm
- **Cause**: Built separately
- **Severity**: 🟡 MEDIUM

### Issue #4: Dev Compose Not Included in Root
- **Problem**: docker-compose.dev.yml is separate, requires explicit `-f` flag
- **Impact**: Developers need to know to use `-f docker-compose.dev.yml`
- **Cause**: Design choice (isolate dev from production)
- **Severity**: 🟡 MEDIUM

### Issue #5: Missing Master Compose
- **Problem**: No single "uber-compose" that brings everything together
- **Impact**: Users don't know how to run the full ecosystem
- **Cause**: Evolved organically without top-level orchestration
- **Severity**: 🔴 CRITICAL

---

## ✅ Solution: Master Integration Strategy

### Phase 1: Consolidate HyperCode-V2.4 (THIS QUARTER)

Create single root compose that includes:
```bash
docker-compose.yml (NEW — root)
  ├─ include: docker-compose.core.yml
  ├─ include: docker-compose.observability.yml
  ├─ include: docker-compose.agents.yml
  └─ (dev via -f flag, optional)
```

**Result**: `docker compose up -d` runs core + observability + agent proxies

### Phase 2: Integrate BROPets

Create `docker-compose.bropets.yml`:
```yaml
services:
  bropets-api:
    build: ../BROskiPets-LLM-dNFT
    networks:
      - agents-net  # Share HyperCode network
    depends_on:
      - redis  # Use HyperCode redis
    environment:
      - REDIS_URL=redis://redis:6379/5  # Separate DB
      - LLM_BASE_URL=http://hypercode-ollama:11434  # Share ollama
```

Then in root compose:
```yaml
include:
  - docker-compose.core.yml
  - docker-compose.agents.yml
  - docker-compose.observability.yml
  - docker-compose.bropets.yml  # NEW
```

### Phase 3: Integrate Obsidian-Brain

Create `docker-compose.brain.yml`:
```yaml
services:
  hyper-brain:
    build: ../BROski-Obsidian-Brain-for-HyperFocus-z0ne
    networks:
      - agents-net
    environment:
      - REDIS_URL=redis://redis:6379/6
      - CORE_URL=http://hypercode-core:8000
```

### Phase 4: Integrate Course Platform

Separate compose or as external service.

### Master Compose Structure

```yaml
# docker-compose.yml (HyperCode-V2.4 root)
include:
  - docker-compose.core.yml            # redis, postgres, core, ollama, celery
  - docker-compose.observability.yml   # prometheus, grafana, loki, tempo
  - docker-compose.agents.yml          # agent proxies, healer, dashboard

networks:
  backend-net:
  data-net:
    internal: true
  agents-net:
  obs-net:
    internal: true
  frontend-net:
```

**Usage:**
```bash
# Start core + observability
docker compose up -d

# Add agents
docker compose --profile agents up -d

# Add pets
docker compose --profile pets up -d

# Add brain
docker compose --profile brain up -d

# Full stack
docker compose --profile agents --profile pets --profile brain up -d
```

---

## 🎯 Action Items (Priority Order)

### IMMEDIATE (This week)

- [ ] Audit all 25 compose files — identify which are actively used
- [ ] Delete/archive unused files (nim.yml?, demo.yml?)
- [ ] Document each file's purpose in a COMPOSE_INVENTORY.md
- [ ] Fix celery-exporter circular dependency ✅ DONE
- [ ] Create docker-compose.bropets.yml (BROPets integration)
- [ ] Create docker-compose.brain.yml (Obsidian-Brain integration)

### SHORT TERM (Next 2 weeks)

- [ ] Consolidate overlapping configs (dev + dev-lite, nano + lean)
- [ ] Create profiles for new integrations: `--profile pets`, `--profile brain`
- [ ] Test full stack with all profiles
- [ ] Update DEPLOYMENT_READINESS.md with BROPets + Brain integration
- [ ] Create COMPOSE_QUICK_REFERENCE.md (which file for what)

### MEDIUM TERM (Month 1)

- [ ] Migrate dev.yml to `--profile dev` in root compose
- [ ] Consolidate monitoring files (monitoring.yml + observability.yml?)
- [ ] Create docker-compose.production.yml (locked versions, no hot-reload)
- [ ] Set up CI/CD to validate all composes on every commit

### LONG TERM (Q2 2026)

- [ ] Consider Kubernetes migration (Helm charts) for large-scale deployment
- [ ] Build unified dashboard to start/stop services visually
- [ ] Implement service mesh (Istio) for advanced networking

---

## 📋 Detailed Analysis: 25 Files Breakdown

### Active/Essential (Should Keep)
- ✅ docker-compose.yml — Root
- ✅ docker-compose.core.yml — Core infra
- ✅ docker-compose.agents.yml — All agents
- ✅ docker-compose.observability.yml — Metrics/logs
- ✅ docker-compose.dev.yml — Development

### Specialized/Optional (Review)
- ⚠️ docker-compose.lean.yml — Minimal? Consolidate with nano?
- ⚠️ docker-compose.nano.yml — Ultra-minimal? Keep for low-resource
- ⚠️ docker-compose.hyper-agents.yml — V2.0 archetypes? Merge into agents.yml?
- ⚠️ docker-compose.hyperhealth.yml — Health monitoring? Merge into observability?
- ⚠️ docker-compose.mcp-gateway.yml — Standalone MCP? Keep if optional feature
- ⚠️ docker-compose.monitoring.yml — Prometheus-specific? Merge into observability?
- ⚠️ docker-compose.demo.yml — Demo mode? Archive or keep as reference?
- ❓ docker-compose.nim.yml — What is this? (Nim language integration?)
- ❓ docker-compose.agents-lite.yml — Lightweight agents? Consolidate?
- ❓ docker-compose.on-demand.yml — On-demand spawning? Advanced feature
- ❓ docker-compose.spawner.yml — Same as on-demand?
- ❓ docker-compose.external-net.yml — External networking? Consolidate?
- ❓ docker-compose.grafana-cloud.yml — Grafana SaaS config? Keep as optional
- ❓ docker-compose.windows.yml — Windows-specific paths? Use env vars instead
- ❓ docker-compose.secrets.yml — Secrets management? Integrate into root
- ❓ + 10 more

**Recommendation**: Audit and document each, then propose consolidation plan.

---

## 🚀 Recommended Directory Structure

```
HyperCode-V2.4/
├── docker-compose.yml                 # Root (includes core, obs, agents)
├── docker-compose.core.yml            # redis, postgres, hypercode-core, ollama, celery
├── docker-compose.observability.yml   # prometheus, grafana, loki, tempo
├── docker-compose.agents.yml          # All 15+ agents
├── docker-compose.dev.yml             # Development with hot-reload
├── docker-compose.production.yml      # Production hardened (new)
├── docker-compose.integrations/       # NEW FOLDER
│   ├── docker-compose.bropets.yml     # BROPets integration (new)
│   ├── docker-compose.brain.yml       # Obsidian-Brain integration (new)
│   ├── docker-compose.course.yml      # Course platform integration (new)
│   └── docker-compose.mcp-gateway.yml # Optional MCP
└── docker-compose.archived/           # OLD FOLDER
    ├── docker-compose.nano.yml        # Archived
    ├── docker-compose.demo.yml        # Archived
    └── ... (other unused files)
```

---

## 📦 BROPets Integration Details

### Current State
```yaml
# BROskiPets-LLM-dNFT/docker-compose.yml
services:
  bropets-api:
    build: .
    ports: ["8080:8080"]
    depends_on: [redis, ollama]
  redis:
    image: redis:7-alpine
  ollama:
    image: ollama/ollama:latest
```

### Problem
- Runs own redis + ollama
- Can't communicate with HyperCode agents
- Duplicate resources

### Solution
```yaml
# HyperCode-V2.4/docker-compose.integrations/docker-compose.bropets.yml
services:
  bropets-api:
    profiles: ["pets"]
    build: ../../BROskiPets-LLM-dNFT
    container_name: bropets-api
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=5                    # Separate namespace
      - LLM_BASE_URL=http://hypercode-ollama:11434  # Share Ollama
    networks:
      - agents-net                    # Share network
      - data-net
    depends_on:
      redis:                          # From core.yml
        condition: service_healthy
      hypercode-ollama:               # From core.yml
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

networks:
  agents-net:
    external: true
    name: hypercode_agents_net
  data-net:
    external: true
    name: hypercode_data_net
```

**Usage:**
```bash
docker compose --profile pets up -d
```

---

## 🧠 Obsidian-Brain Integration Details

### Current State
```yaml
# BROski-Obsidian-Brain-for-HyperFocus-z0ne/docker-compose.hyper-brain.yml
services:
  hyper-brain:
    build: .
    ports: ["8100:8100"]
    environment:
      - OBSIDIAN_VAULT_PATH=/vault
      - REDIS_URL=redis://redis:6379/4
```

### Solution
```yaml
# HyperCode-V2.4/docker-compose.integrations/docker-compose.brain.yml
services:
  hyper-brain:
    profiles: ["brain"]
    build: ../../BROski-Obsidian-Brain-for-HyperFocus-z0ne
    container_name: hyper-brain
    ports:
      - "127.0.0.1:8100:8100"
    environment:
      - OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH}  # From .env
      - REDIS_URL=redis://redis:6379/4              # Share Redis
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - GITHUB_PAT=${GITHUB_PAT}
    volumes:
      - ${OBSIDIAN_VAULT_PATH}:/vault
    networks:
      - agents-net
      - data-net
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

networks:
  agents-net:
    external: true
    name: hypercode_agents_net
  data-net:
    external: true
    name: hypercode_data_net
```

---

## 📊 Complete Service Map (After Integration)

### Always-On Services (Default `docker compose up -d`)
- redis
- postgres
- hypercode-core
- hypercode-ollama
- celery-worker
- prometheus
- grafana
- loki
- tempo
- docker-socket-proxy
- healer-agent
- dashboard

### Profile: agents (`--profile agents`)
- 15+ AI agents (coder, frontend-specialist, backend-specialist, etc.)
- crew-orchestrator
- mcp-gateway

### Profile: pets (`--profile pets`)
- bropets-api

### Profile: brain (`--profile brain`)
- hyper-brain
- (optional) github-sync

### Profile: discord (`--profile discord`)
- broski-bot

### Profile: mission (`--profile mission`)
- hyper-mission-api
- hyper-mission-ui

### Profile: dev (`--profile dev`)
- hypercode-core-dev (hot-reload)
- agents-dev (hot-reload)
- redis-commander
- pgadmin
- mailhog
- nginx-dev
- docs-server

---

## 🔄 Recommended Rollout Sequence

**Week 1:**
1. Document all 25 files
2. Create BROPets integration compose
3. Create Obsidian-Brain integration compose
4. Test with `--profile pets --profile brain`

**Week 2:**
1. Consolidate nano/lean/demo files
2. Move dev compose to profile
3. Full stack testing

**Week 3:**
1. Production hardening (locked versions, secrets)
2. CI/CD validation
3. Documentation

---

## 📋 Checklist

- [ ] Run diagnostics on all 25 compose files
- [ ] Identify actively used vs. archived
- [ ] Create COMPOSE_INVENTORY.md
- [ ] Create docker-compose.bropets.yml
- [ ] Create docker-compose.brain.yml
- [ ] Test integration: core + pets
- [ ] Test integration: core + brain
- [ ] Test integration: core + agents + pets + brain
- [ ] Update root compose to include integrations
- [ ] Update DEPLOYMENT_READINESS.md
- [ ] Archive unused files
- [ ] Create COMPOSE_QUICK_REFERENCE.md

---

**Status**: 🔴 FRAGMENTED → 🟡 IN PROGRESS → 🟢 UNIFIED (Target: End of Week)

