# 🚀 BUILD & RUN ALL 12 GHOST AGENTS — Complete Guide

**Quick Start (after images build):**
```bash
cd HyperCode-V2.4
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d
```

---

## The 12 Missing Ghost Agents

Your ecosystem was missing 12 AI agents that form the complete agent squad. All 12 now have:
- ✓ Dockerfiles verified
- ✓ Build pipeline initiated
- ✓ Source code in place
- 🔨 Images being built

---

## Agent Roster

### Profile `agents` — Main specialists (8 agents)
```
:8007  Security Engineer
:8008  System Architect
:8080  Test Agent
:8014  Throttle Agent
:8009  Tips & Tricks Writer
:8015  Super Hyper BROski
[+2 more already running]
```

### Profile `hyper` — Hyper-focus powered (6 agents)
```
:8091  Hyper Architect
:8092  Hyper Observer
:8093  Hyper Worker
:8096  Hyper Split Agent
:8097  Session Snapshot
[+Agent X with custom routing]
```

---

## Where The Builds Are

`HyperCode-V2.4/agents/` contains 38 agent directories:

| Agent | Directory | Status |
|-------|-----------|--------|
| Security Engineer | `06-security-engineer/` | ✓ Image ready |
| System Architect | `07-system-architect/` | 🔨 Building |
| Test Agent | `test-agent/` | 🔨 Building |
| Throttle Agent | `throttle-agent/` | 🔨 Building |
| Tips & Tricks Writer | `09-tips-tricks-writer/` | 🔨 Building |
| Super Hyper BROski | `super-hyper-broski-agent/` | 🔨 Building |
| Hyper Architect | `architect/` | 🔨 Building |
| Hyper Observer | `hyper-agents/hyper-observer/` | 🔨 Building |
| Hyper Worker | `hyper-agents/hyper-worker/` | 🔨 Building |
| Hyper Split Agent | `hyper-split-agent/` | 🔨 Building |
| Session Snapshot | `session-snapshot/` | 🔨 Building |
| Agent X | `agent-x/` | 🔨 Building |

---

## What Each Build Does

Each Docker build:
1. Pulls `python:3.11-slim` base image
2. Installs OS dependencies (gcc, g++, curl, etc.)
3. Caches Python wheels via pip cache mount
4. Installs agent-specific dependencies from `requirements.txt`
5. Copies agent code (agent.py, config.json, hive_mind/, memory/)
6. Runs health checks
7. Produces optimized runtime image

**Typical build time:** 3–10 minutes per agent  
**Total time for 11 agents:** 30–60 minutes (sequential)

---

## Once Builds Complete

### 1. Verify all images exist
```bash
docker images | grep hypercode-v24- | wc -l
# Should be 25+ (full squad)
```

### 2. Start the full stack
```bash
cd HyperCode-V2.4

# Method A: Full agents squad (25 agents + all infrastructure)
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d

# Method B: Lite agents (just the essential profile)
docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d --profile agents

# Method C: Hyper profile only (Hyper Architect, Observer, Worker, etc.)
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d --profile hyper
```

### 3. Watch them boot
```bash
docker compose logs -f --tail=50
```

### 4. Verify all healthy
```bash
# Check container status
docker compose ps | grep -i agent

# Test agent endpoints (all should return 200)
for port in 8007 8008 8080 8014 8009 8015 8091 8092 8093 8096 8097; do
  echo "Port :$port"
  curl -s http://127.0.0.1:$port/health | head -c 50
done
```

---

## Next Steps

### Short term:
- [ ] All 11 images finish building (auto-happening now)
- [ ] Run `docker compose up -d` once builds complete
- [ ] Verify all 12 agents pass health checks
- [ ] Confirm agent-to-agent networking works

### Medium term:
- [ ] Load HYPER-SILLs skill vault into all agents
- [ ] Test agent orchestration (crew-orchestrator coordination)
- [ ] Verify webhook integration (coderabbit, stripe, etc.)
- [ ] Test multi-agent workflows

### Long term:
- [ ] Integrate with Dashboard UI (:8088)
- [ ] Set up monitoring (Prometheus :9090, Grafana :3001)
- [ ] Configure Discord bot (broski-bot)
- [ ] Wire up to Course DB (Supabase)

---

## Troubleshooting

### A build fails with "not found"
Check the Dockerfile context — it expects to run from HyperCode-V2.4 root:
```bash
cd HyperCode-V2.4  # MUST be here
docker build -t hypercode-v24-test-agent:latest -f agents/test-agent/Dockerfile .
#                                                                              ^ dot = context
```

### Image builds but container won't start
```bash
docker logs <container_name>
# Common issues:
#   - Missing env vars → check .env file
#   - Port already in use → kill old container
#   - Memory limit exceeded → increase Docker memory
```

### Compose validation error
The main docker-compose.yml has a known prometheus config issue. Use the agents-full.yml to bypass:
```bash
# This works:
docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d

# This fails (validation error in prometheus.security_opt):
docker compose up -d
```

---

## Architecture

```
HyperCode-V2.4 (backend + 25-agent swarm)
    ├── Core Infrastructure
    │   ├── redis (state + task queue)
    │   ├── postgres (event store)
    │   ├── minio (file storage)
    │   └── ollama (local LLM)
    │
    ├── Tier 1: Core Crew (5 agents)
    │   ├── crew-orchestrator (8081 — master coordinator)
    │   ├── agent-x (custom routing)
    │   ├── brain-agent (memory)
    │   ├── coder-agent (code specialist)
    │   └── tips-tricks-writer
    │
    ├── Tier 2: Specialists (7 agents)
    │   ├── security-engineer (8007) 🔨
    │   ├── system-architect (8008) 🔨
    │   ├── frontend-specialist (8003)
    │   ├── backend-specialist (8004)
    │   ├── database-architect (8005)
    │   ├── qa-engineer (8006)
    │   └── devops-engineer (8012)
    │
    ├── Tier 3: Hyper-Powered (6 agents)
    │   ├── hyper-architect (8091) 🔨
    │   ├── hyper-observer (8092) 🔨
    │   ├── hyper-worker (8093) 🔨
    │   ├── hyper-split-agent (8096) 🔨
    │   ├── session-snapshot (8097) 🔨
    │   └── goal-keeper (8010)
    │
    └── Support & Control (7 agents)
        ├── test-agent (8080) 🔨
        ├── throttle-agent (8014) 🔨
        ├── super-hyper-broski-agent (8015) 🔨
        ├── project-strategist (8011)
        ├── mcp-server (core)
        ├── broski-bot (Discord)
        └── coderabbit-webhook (GitHub)

🔨 = Currently building
```

---

## Rebuild Manually (any agent)

```bash
# From HyperCode-V2.4 root, rebuild any agent
docker build \
  -t hypercode-v24-AGENT_NAME:latest \
  -f agents/AGENT_DIR/Dockerfile \
  .
```

Example:
```bash
docker build -t hypercode-v24-test-agent:latest -f agents/test-agent/Dockerfile .
```

---

## Performance Notes

- **RAM usage:** ~8GB for full 25-agent squad (with profiles)
- **Disk space:** ~50GB for all images + runtime data
- **Network:** All agents on isolated `agents-net` bridge
- **Healthchecks:** All agents report to `:9090` Prometheus

---

## Questions?

Check:
- `HyperCode-V2.4/AGENTS_BUILD_STATUS.md` — live build status
- `HyperCode-V2.4/CLAUDE.md` — architecture & design
- `HyperCode-V2.4/WHATS_DONE.md` — what's already built
- `HyperCode-V2.4/README.md` — getting started

---

**Built by @welshDog | HyperCode V2.4**  
*"Stop apologizing for your brain. Start building."* 🧠♾️
