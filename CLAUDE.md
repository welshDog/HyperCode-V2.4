# 🦅 HyperCode V2.4 — Claude AI Project Intelligence

> This file is auto-read by Claude AI when analysing this repository.
> It provides essential project context, conventions, and guidance.
> **Last updated: April 14, 2026 — Phase 10C COMPLETE ✅**

---

## 🎯 Project Identity

**HyperCode V2.4** is a neurodivergent-first, AI-powered, open-source programming ecosystem.

- **Creator:** Lyndz Williams (@welshDog), Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- **Brain style:** ADHD + Dyslexia + Pattern thinker + Big vision
- **Core mission:** Build a cognitive AI architecture that evolves itself
- **License:** See LICENSE file
- **Communication style:** Short sentences, emojis, bold keys, quick wins first. Call Lyndz "Bro".

---

## ✅ CURRENT STATUS: FULLY OPERATIONAL (April 14, 2026)

> 🟢 ALL 23 CONTAINERS HEALTHY — Stack is LIVE!

### Phase 10C — Docker Secrets — COMPLETE ✅

All infrastructure is running. Full stack confirmed healthy on April 14, 2026.

| Container | Status |
|---|---|
| postgres | ✅ Healthy |
| redis | ✅ Healthy |
| hypercode-core | ✅ Healthy |
| celery-worker | ✅ Healthy |
| prometheus | ✅ Healthy |
| grafana | ✅ Running |
| hypercode-ollama | ✅ Healthy |
| healer-agent | ✅ Running |
| hypercode-dashboard | ✅ Running |
| hypercode-mcp-server | ✅ Running |
| minio, chroma, loki, tempo, promtail | ✅ All Running |
| cadvisor, node-exporter, alertmanager | ✅ All Running |
| docker-socket-proxy | ✅ Running |

### What Fixed The Stack (For Claude's Reference)

1. **`POSTGRES_PASSWORD_FILE` + `POSTGRES_PASSWORD` conflict** — Removed `_FILE` override from postgres in `docker-compose.secrets.yml`. Postgres uses plain env var from `.env` only.
2. **`.env` broken line** — `POSTGRES_PASSWORD` was concatenated onto `MISSION_CONTROL_URL` with no newline. Fixed manually in nano.
3. **Special chars in password** — Password contains `/`, `+`, `=` — must be quoted in `.env`: `POSTGRES_PASSWORD="..."`
4. **Stale postgres data volume** — Wiped using Alpine container (no sudo): `docker run --rm -v "/path/to/volumes/postgres":/target alpine sh -c "rm -rf /target/*"`
5. **`POSTGRES_USER` missing** — Added `POSTGRES_USER=postgres` to `.env`

### Core API Confirmed Working
```json
{"status":"ok","service":"hypercode-core","version":"2.0.0","environment":"development"}
```

### Start Command (Always Use This)
```bash
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

### Volumes Location
```
H:/HyperStation zone/HyperCode/volumes/
```
In WSL: `/mnt/h/HyperStation zone/HyperCode/volumes/`

---

## 🚀 NEXT PHASE: Agents Security Upgrade

> ⚠️ READ THIS BEFORE TOUCHING ANY DOCKERFILE OR AGENT FILE!

### Mission Objective
Patch all 12 agent Docker images to eliminate CRITICAL CVEs found in Trivy scan (April 14, 2026).

### Agent Image Scan Results — Priority Order

| Priority | Image | CRITICAL | HIGH | Action |
|----------|-------|----------|------|--------|
| 🔴 1 | `hypercode-v24-agent-x` | **11** | 55 | Patch NOW |
| 🔴 2 | `hypercode-v24-celery-worker` | TBC | HIGH | Patch |
| 🔴 3 | `hypercode-v24-crew-orchestrator` | TBC | HIGH | Patch |
| 🔴 4 | `hypercode-v24-healer-agent` | TBC | HIGH | Patch |
| 🟡 5 | `hypercode-v24-broski-bot` | 0 | 51 | Patch |
| 🟡 6 | `hypercode-v24-hyper-architect` | TBC | - | Patch |
| 🟡 7 | `hypercode-v24-hyper-observer` | TBC | - | Patch |
| 🟡 8 | `hypercode-v24-hyper-worker` | TBC | - | Patch |
| 🟡 9 | `hypercode-v24-hypercode-mcp-server` | TBC | - | Patch |
| 🟡 10 | `hypercode-v24-test-agent` | TBC | - | Patch |
| 🟡 11 | `hypercode-v24-throttle-agent` | TBC | - | Patch |
| 🟡 12 | `hypercode-v24-tips-tricks-writer` | TBC | - | Patch |

### Key CVEs Found
- `libexpat1` — **CRITICAL** CVE-2024-45491, CVE-2024-45492 (Integer Overflow)
- `libc6` / `libc-bin` — **HIGH** CVE-2024-2961 (glibc out-of-bounds write)
- `libssl3` / `openssl` — **HIGH** multiple CVEs
- `docker.io` (moby) — **HIGH** CVE-2024-24557, CVE-2024-29018
- `gpgv` — **HIGH** CVE-2025-68973 (fixed — needs apt upgrade)

### Target: ZERO CRITICAL, <5 HIGH after patch phase

---

## 🔐 Security Standards — MANDATORY FOR ALL DOCKERFILES

> Claude: ALWAYS apply these rules when writing or editing any Dockerfile.

### Rule 1 — Base Image
```dockerfile
# ✅ CORRECT — always use pinned slim bookworm
FROM python:3.11-slim

# ❌ NEVER use untagged latest or old images
FROM python:latest
FROM python:3.11  # (without -slim)
```

### Rule 2 — OS Package Hardening (add to EVERY Dockerfile after FROM)
```dockerfile
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Rule 3 — Pip Tool Hardening
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    pip==26.0.1 \
    setuptools>=80.0.0 \
    wheel==0.46.2
```

### Rule 4 — Never Run as Root
```dockerfile
# Always create and use a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

### Rule 5 — Security Scanner
- Tool: **Trivy** (running as `hyper-shield-scanner` container)
- Scan command: `docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet <image>`
- Run after EVERY Dockerfile change to verify fix
- Target: **ZERO CRITICAL, <5 HIGH**

---

## 🧬 Architecture Overview

### Core Services

| Service | Port | Purpose |
|---|---|---|
| HyperCode Core (FastAPI) | 8000 | Main backend, memory hub, integrations |
| Agent X (Meta-Architect) | 8080 | Designs & deploys AI agents autonomously |
| Crew Orchestrator | 8081 | Agent lifecycle + task execution |
| Healer Agent | 8008 | Self-healing — monitors & auto-recovers services |
| BROski Terminal (CLI UI) | 3000 | Custom terminal interface |
| Mission Control Dashboard | 8088 | Next.js/React real-time dashboard |
| Grafana Observability | 3001 | Metrics, alerts, dashboards |

### Infrastructure Stack
- **Containers:** Docker Compose (multi-file strategy) — 23 containers active
- **Databases:** Redis (pub/sub + cache) + PostgreSQL (persistent memory)
- **Observability:** Prometheus + Grafana + custom health reports
- **Secrets:** `docker-compose.secrets.yml` + `./secrets/*.txt` files
- **MCP Gateway:** Full Model Context Protocol server integration
- **Kubernetes:** Helm charts in `k8s/` and `helm/` (scale path)
- **Security:** Trivy scanner (`hyper-shield-scanner`) — scans all 12 agent images

---

## 📁 Directory Structure Guide

```
HyperCode-V2.4/
├── .claude/                    # Claude AI config & skills
│   ├── settings.local.json     # Claude permissions & MCP config
│   └── skills/                 # Skill modules for Claude
├── agents/                     # All AI agent definitions
├── backend/                    # FastAPI core backend
├── broski-business-agents/     # Business automation agents
├── cli/                        # BROski Terminal CLI
├── config/                     # App configuration files
├── dashboard/                  # Mission Control (Next.js)
├── docs/                       # Documentation
├── grafana/                    # Grafana dashboards & config
├── hyper-mission-system/       # Mission/quest gamification engine
├── Hyper-Agents-Box/           # Agent sandbox & experiments
├── hyperstudio-platform/       # Creative platform components
├── k8s/                        # Kubernetes manifests
├── helm/                       # Helm charts
├── mcp/                        # MCP server implementations
├── monitoring/                 # Prometheus config & alert rules
├── nginx/                      # Nginx reverse proxy config
├── quantum-compiler/           # Quantum computing experiments
├── scripts/                    # Dev & ops shell scripts
├── security/                   # Security scanning & secrets
├── services/                   # Microservice implementations
├── src/                        # Shared source modules
├── templates/                  # Jinja/HTML templates
├── tests/                      # Test suite (pytest)
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── framework/              # LLM eval stubs
├── tools/                      # Developer tooling
└── verification/               # Deployment verification scripts
```

---

## 🧭 Claude Auto-Discovery Map

When working in this repo, treat these as the "always read first" entrypoints:

- Claude project context: [CLAUDE.md](CLAUDE.md)
- Claude full context + history: [CLAUDE_CONTEXT.md](CLAUDE_CONTEXT.md)
- Claude config + skills: [.claude/README.md](.claude/README.md)
- Agents overview + conventions: [agents/README.md](agents/README.md)
- Ops/dev scripts index: [scripts/README.md](scripts/README.md)
- Documentation hub: [docs/index.md](docs/index.md)

---

## 🛠️ Development Commands

### Quick Start
```bash
# Core stack — ALWAYS use secrets override
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Core + all agents
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile agents up -d

# Core + hyper agents
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile hyper up -d

# Full stack (everything)
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile agents --profile hyper --profile health --profile mission up -d
```

### Security Scanning
```bash
# Scan a single image
docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet hypercode-v24-agent-x

# Scan ALL 12 agent images (PowerShell)
$images = @("hypercode-v24-agent-x","hypercode-v24-broski-bot","hypercode-v24-celery-worker",
             "hypercode-v24-crew-orchestrator","hypercode-v24-healer-agent","hypercode-v24-hyper-architect",
             "hypercode-v24-hyper-observer","hypercode-v24-hyper-worker","hypercode-v24-hypercode-mcp-server",
             "hypercode-v24-test-agent","hypercode-v24-throttle-agent","hypercode-v24-tips-tricks-writer")
foreach ($img in $images) { docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet $img }
```

### Testing
```bash
# All tests
python -m pytest tests/ --tb=short -q

# Unit tests only
python -m pytest tests/unit/ -v --tb=short

# Integration tests
python -m pytest tests/integration/ -q
```

---

## 🧠 Code Conventions

### Python
- **Formatter:** Ruff (`ruff.toml`)
- **Linter:** Pylint (`.pylintrc`) + Ruff
- **Type checker:** Pyright (`pyrightconfig.json`)
- **Test runner:** pytest (`pytest.ini`)
- **Python version:** 3.11 in Docker images (3.13+ in devcontainer)
- **Package manager:** pip with `requirements.lock` for deterministic builds

### Async Patterns
- All agent communication uses `async/await`
- Redis pub/sub for real-time agent messaging
- FastAPI background tasks for long-running agent jobs

### Agent Naming Conventions
- Agent files: `snake_case.py`
- Agent classes: `PascalCaseAgent`
- Agent endpoints: `/agents/{agent_name}/{action}`

### Docker Compose Strategy

**Multi-file strategy** — always combine base + secrets override.

| Profile | Command | Services |
|---------|---------|---------|
| *(none)* | `docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d` | Core infra + observability + MCP server |
| `agents` | add `--profile agents` | All specialist agents |
| `hyper` | add `--profile hyper` | Hyper-architect, observer, worker, agent-x |
| `health` | add `--profile health` | HyperHealth API + worker |
| `mission` | add `--profile mission` | HyperMission API + UI |
| `discord` | add `--profile discord` | Broski Discord bot |

---

## 🔑 Key Dependencies

### Python (from requirements files)
- `fastapi` + `uvicorn` — async web framework
- `pydantic` — data validation & settings
- `redis` / `aioredis` — Redis async client
- `sqlalchemy` / `asyncpg` — PostgreSQL async ORM
- `openai` — OpenAI-compatible API client
- `anthropic` — Claude API client
- `mcp` — Model Context Protocol SDK
- `pytest` + `fakeredis` — testing

### Node.js (dashboard)
- `next.js` — React framework for Mission Control
- `vitest` — unit testing
- TypeScript throughout

---

## 🚀 MCP Integration

HyperCode exposes its own MCP server (`hypercode` in `.mcp.json`).

Available MCP tools:
- `mcp__hypercode__hypercode_system_health` — full system health check
- `mcp__hypercode__hypercode_agent_system_health` — agent-specific health
- `mcp__hypercode__hypercode_list_agents` — list all registered agents
- `mcp__hypercode__hypercode_list_tasks` — list active tasks

---

## ⚠️ Known Issues & Gotchas

1. **Windows path handling** — Use `docker-compose.windows.yml` override on Windows
2. **Secrets management** — Never commit `.env` files; secrets live in `./secrets/*.txt`
3. **POSTGRES_PASSWORD** — Must be plain in `.env` (quoted if it contains special chars). Do NOT use `POSTGRES_PASSWORD_FILE` alongside it — postgres treats them as exclusive.
4. **Agent boot order** — Redis and PostgreSQL must be healthy before agents start
5. **Port conflicts** — Ensure ports 3000, 3001, 8000, 8008, 8080, 8081, 8088 are free
6. **Test environment** — `fakeredis` used in tests; import via `fakeredis.aioredis`
7. **Docker imports** — ALWAYS `from app.X import Y` — NEVER `from backend.app.X import Y`
8. **FastAPI routing** — First-match wins — public routes BEFORE auth-gated compat routes
9. **Volumes wipe** — Use Alpine container trick (no sudo needed): `docker run --rm -v "/path":/target alpine sh -c "rm -rf /target/*"`

---

## 🎮 Gamification System

- **BROski$ coins** — earned by completing tasks, agent milestones, commits
- **XP levels** — track developer + system progression
- **Achievements** — unlocked by specific actions in the hyper-mission-system
- **Mission Control** — real-time dashboard showing all active quests
- 🏆 Celebrate wins! Every patched CVE = BROski$ earned!

---

## 📚 Further Reading

- [README.md](README.md) — Main project overview
- [CLAUDE_CONTEXT.md](CLAUDE_CONTEXT.md) — Full history, rules, paths
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [SECURITY.md](SECURITY.md) — Security policy
- [docs/claude-integration/](docs/claude-integration/) — Claude AI integration guide
