# 🦅 HyperCode V2.0 — Claude AI Project Intelligence

> This file is auto-read by Claude AI when analysing this repository.
> It provides essential project context, conventions, and guidance.

---

## 🎯 Project Identity

**HyperCode V2.0** is a neurodivergent-first, AI-powered, open-source programming ecosystem.

- **Creator:** Lyndz Williams (@welshDog), Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- **Brain style:** ADHD + Dyslexia + Pattern thinker + Big vision
- **Core mission:** Build a cognitive AI architecture that evolves itself
- **License:** See LICENSE file

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
- **Containers:** Docker Compose (multi-file strategy)
- **Databases:** Redis (pub/sub + cache) + PostgreSQL (persistent memory)
- **Observability:** Prometheus + Grafana + custom health reports
- **Reverse Proxy:** Nginx
- **CI/CD:** GitHub Actions (`.github/`), Husky pre-commit hooks
- **MCP Gateway:** Full Model Context Protocol server integration
- **Kubernetes:** Helm charts in `k8s/` and `helm/` (scale path)

---

## 📁 Directory Structure Guide

```
HyperCode-V2.0/
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

When working in this repo, treat these as the “always read first” entrypoints:

- Claude project context: [CLAUDE.md](CLAUDE.md)
- Claude config + skills: [.claude/README.md](.claude/README.md)
- Agents overview + conventions: [agents/README.md](agents/README.md)
- Ops/dev scripts index: [scripts/README.md](scripts/README.md)
- Documentation hub: [docs/index.md](docs/index.md) (also [docs/README.md](docs/README.md))

## 🛠️ Development Commands

### Quick Start
```bash
# Core stack (infra + observability + MCP)
docker compose up -d

# Core + all agents
docker compose --profile agents up -d

# Core + hyper agents (architect, observer, worker, agent-x)
docker compose --profile hyper up -d

# Full stack (everything)
docker compose --profile agents --profile hyper --profile health --profile mission up -d

# Windows path overrides
docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d
```

### Testing
```bash
# All tests
python -m pytest tests/ --tb=short -q

# Unit tests only
python -m pytest tests/unit/ -v --tb=short

# Integration tests
python -m pytest tests/integration/ -q

# Specific test file
python -m pytest tests/unit/test_broski_service.py -q --tb=short
```

### Make Targets
```bash
make help              # List all make targets
make dev               # Start dev environment
make test              # Run test suite
make observability     # Start Grafana/Prometheus stack
```

---

## 🧠 Code Conventions

### Python
- **Formatter:** Ruff (`ruff.toml`)
- **Linter:** Pylint (`.pylintrc`) + Ruff
- **Type checker:** Pyright (`pyrightconfig.json`)
- **Test runner:** pytest (`pytest.ini`)
- **Python version:** 3.13+ (see `.devcontainer`)
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

**Single-file with profiles** — `docker-compose.yml` is the canonical stack.

| Profile | Command | Services |
|---------|---------|---------|
| *(none)* | `docker compose up -d` | Core infra + observability + MCP server |
| `agents` | `docker compose --profile agents up -d` | All specialist agents |
| `hyper` | `docker compose --profile hyper up -d` | Hyper-architect, observer, worker, agent-x |
| `health` | `docker compose --profile health up -d` | HyperHealth API + worker |
| `mission` | `docker compose --profile mission up -d` | HyperMission API + UI |
| `discord` | `docker compose --profile discord up -d` | Broski Discord bot |
| `nim` | `docker compose --profile nim up -d` | NVIDIA NIM LLM service |

**Overlay files** (use alongside main with `-f`):
- `docker-compose.dev.yml` — dev environment (hot-reload, pgadmin, mailhog)
- `docker-compose.monitoring.yml` — full monitoring stack alternative
- `docker-compose.mcp-gateway.yml` — extended MCP gateway stack
- `docker-compose.agents.yml` — self-contained standalone agent stack
- `docker-compose.nano.yml` — ultra-low RAM overrides (<4GB)
- `docker-compose.secrets.yml` — Docker secrets overlay (production)
- `docker-compose.windows.yml` — Windows path overrides

**Archived** (obsolete, see `docs/archive/docker/`):
- `docker-compose.health.yml`, `docker-compose.mcp-full.yml`, `docker-compose.agents-test.yml`

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

See `.mcp.json` for server connection config.

---

## ⚠️ Known Issues & Gotchas

1. **Windows path handling** — Use `docker-compose.windows.yml` override on Windows; some volume paths differ
2. **Secrets management** — Never commit `.env` files; use `docker-compose.secrets.yml` overlay + Docker secrets in production
3. **Agent boot order** — Redis and PostgreSQL must be healthy before agents start; health checks are defined in compose files
4. **Port conflicts** — Ensure ports 3000, 3001, 8000, 8008, 8080, 8081, 8088 are free before starting
5. **Test environment** — `fakeredis` used in tests to avoid needing live Redis; import it via `fakeredis.aioredis`

---

## 🎮 Gamification System

- **BROski$ coins** — earned by completing tasks, agent milestones, commits
- **XP levels** — track developer + system progression
- **Achievements** — unlocked by specific actions in the hyper-mission-system
- **Mission Control** — real-time dashboard showing all active quests

---

## 📚 Further Reading

- [README.md](README.md) — Main project overview
- [README_INFRASTRUCTURE_UPGRADE.md](README_INFRASTRUCTURE_UPGRADE.md) — Infrastructure deep dive
- [README_OBSERVABILITY.md](README_OBSERVABILITY.md) — Grafana/Prometheus setup
- [README_HEALTH_REPORTS.md](README_HEALTH_REPORTS.md) — Health monitoring guide
- [SUPER_HYPER_BROSKI_AGENT_README.md](SUPER_HYPER_BROSKI_AGENT_README.md) — BROski agent docs
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [docs/claude-integration/](docs/claude-integration/) — Claude AI integration guide
