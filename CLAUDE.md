# 🦅 HyperCode V2.4 — Claude AI Project Intelligence

> This file is auto-read by Claude AI when analysing this repository.
> It provides essential project context, conventions, and guidance.
> **Last updated: April 14, 2026 — Phases 10D + 10G + 10H COMPLETE ✅ | Stripe + Agent Auth + Pricing LIVE**
> **Single source of truth — merged from CLAUDE.md + CLAUDE_CONTEXT.md**

---

## 🧠 Who You're Talking To

- **Lyndz** aka BROski♾️ (GitHub: @welshDog, npm: @w3lshdog) — Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them **"Bro"** — that's how we roll
- Short sentences. Emojis. Bold the key stuff. Celebrate wins! 🎉
- **Brain style:** Pattern thinker + Big vision + Neurodivergent-first

---

## 🎯 Project Identity

**HyperCode V2.4** is a neurodivergent-first, AI-powered, open-source programming ecosystem.

- **Creator:** Lyndz Williams (@welshDog), Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- **Core mission:** Build a cognitive AI architecture that evolves itself
- **License:** See LICENSE file
- **Communication style:** Short sentences, emojis, bold keys, quick wins first. Call Lyndz "Bro".

---

## 🌐 The Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel)                    │                  (Docker, 26 containers)
Path: H:\the hyper vibe coding hub     │                  Path: H:\HyperStation zone\
                                       │                       HyperCode\HyperCode-V2.4
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.4
                          Path: H:\HyperAgent-SDK
```

---

## ✅ CURRENT STATUS: FULLY OPERATIONAL (April 14, 2026)

> 🟢 ALL 23 CONTAINERS HEALTHY — Stack is LIVE!

### 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| 6 | Terminal Tools Integration | ✅ DONE + VERIFIED LIVE |
| 7 | Dockerfile Security Hardening | ✅ DONE — April 14, 2026 |
| 8 | CI/CD Trivy Security Pipeline | ✅ DONE — April 14, 2026 |
| 9 | CVE Elimination (apt + pip pinning) | ✅ DONE — April 14, 2026 |
| 10A | FastAPI / Starlette upgrade | ✅ DONE |
| 10B | Docker Compose Network Isolation | ✅ DONE — April 14, 2026 |
| 10C | Docker Secrets | ✅ DONE — April 14, 2026 |
| 10F | **Stripe Checkout API** | ✅ DONE — April 14, 2026 💳 |
| 10G | **DB — Stripe webhook writes** | ✅ DONE — April 14, 2026 |
| 10D | **Agent-level rate limiting + auth** | ✅ DONE — April 14, 2026 🔑 |
| 10H | **Pricing page (dashboard)** | ✅ DONE — April 14, 2026 |

### Container Health

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

## 🎯 NEXT UP — Remaining Phases

| Phase | Task | Why |
|---|---|---|
| **10I** | Stripe CLI end-to-end local testing | `stripe listen --forward-to localhost:8000/api/stripe/webhook` |
| **10C** | Docker Secrets — productionise env vars | `.env` still used locally, need secrets/*.txt for prod |
| **CVE** | Agent image CVE patching | 14 HIGH remaining on agent images (no Debian fix yet) |

### Agents Security Upgrade

> ⚠️ READ THIS BEFORE TOUCHING ANY DOCKERFILE OR AGENT FILE!

| Priority | Image | CRITICAL | HIGH | Action |
|----------|-------|----------|------|--------|
| 🔴 1 | `hypercode-v24-agent-x` | **11** | 55 | Patch NOW |
| 🔴 2 | `hypercode-v24-celery-worker` | TBC | HIGH | Patch |
| 🔴 3 | `hypercode-v24-crew-orchestrator` | TBC | HIGH | Patch |
| 🔴 4 | `hypercode-v24-healer-agent` | TBC | HIGH | Patch |
| 🟡 5-12 | All remaining agent images | TBC | - | Patch |

**Target: ZERO CRITICAL, <5 HIGH after patch phase**

---

## 💳 Phase 10F — Stripe Checkout API (LIVE)

### Live Endpoints
```
POST /api/stripe/checkout    → creates Stripe Checkout Session, returns URL
GET  /api/stripe/plans       → lists available plan names
POST /api/stripe/webhook     → handles Stripe events (signature verified)
```

### Webhook events handled
- `checkout.session.completed` → subscription activated (TODO 10G: write to DB)
- `customer.subscription.deleted` → subscription cancelled
- `invoice.payment_failed` → payment failed warning
- `customer.subscription.updated` → status change logged

### 🔒 Stripe Prices — LOCKED (April 14, 2026)

| Pack | Price | Tokens | Stripe Product |
|---|---|---|---|
| Starter | £5 GBP | 200 | BROski Starter Pack |
| Builder | £15 GBP | 800 | BROski Builder Pack |
| Hyper | £35 GBP | 2500 | BROski Hyper Pack |

| Tier | Monthly | Yearly |
|---|---|---|
| Pro | £9/mo | £90/yr |
| Hyper | £29/mo | £290/yr |

### .env keys to add
```env
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_BUILDER=price_xxx
STRIPE_PRICE_HYPER=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_HYPER_MONTHLY=price_xxx
STRIPE_PRICE_HYPER_YEARLY=price_xxx
```

---

## 🔐 Security Standards — MANDATORY FOR ALL DOCKERFILES

> Claude: ALWAYS apply these rules when writing or editing any Dockerfile.

### Rule 1 — Base Image
```dockerfile
# ✅ CORRECT
FROM python:3.11-slim

# ❌ NEVER
FROM python:latest
```

### Rule 2 — OS Package Hardening (Part A — every runtime stage)
```dockerfile
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

### Rule 3 — Pip Tool Hardening (Part B — every Python runtime stage)
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"
```

### Rule 4 — Never Run as Root
```dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

### Rule 5 — Security Scanner
- Tool: **Trivy** (running as `hyper-shield-scanner` container)
- Scan: `docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet <image>`
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
- **Containers:** Docker Compose (multi-file strategy) — 23-26 containers active
- **Databases:** Redis (pub/sub + cache) + PostgreSQL (persistent memory)
- **Observability:** Prometheus + Grafana + custom health reports
- **Secrets:** `docker-compose.secrets.yml` + `./secrets/*.txt` files
- **Networks:** 5 isolated networks — `data-net` + `obs-net` are `internal: true`
- **MCP Gateway:** Full Model Context Protocol server integration
- **Kubernetes:** Helm charts in `k8s/` and `helm/` (scale path)
- **Security:** Trivy scanner (`hyper-shield-scanner`) — scans all 12 agent images
- **Stripe:** LIVE at `/api/stripe/checkout` — Phase 10F ✅

### 🌐 Phase 10B — Docker Network Topology

- `frontend-net` (bridge, internet) — dashboard, mission-ui, mcp-server
- `backend-net` (bridge, internet) — hypercode-core (bridges all layers)
- `agents-net` (bridge, internet) — all AI agents, LLM API calls
- `data-net` (bridge, **internal: true**) — redis + postgres + minio + chroma
- `obs-net` (bridge, **internal: true**) — prometheus, grafana, loki, tempo, promtail

Script: `scripts/network-migrate.sh`

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
├── k8s/                        # Kubernetes manifests
├── helm/                       # Helm charts
├── mcp/                        # MCP server implementations
├── monitoring/                 # Prometheus config & alert rules
├── scripts/                    # Dev & ops shell scripts
├── security/                   # Security scanning & secrets
├── services/                   # Microservice implementations
├── tests/                      # Test suite (pytest)
└── tools/                      # Developer tooling
```

---

## 🛠️ Development Commands

### Quick Start
```bash
# Core stack
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# Core + all agents
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile agents up -d

# Full stack
docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile agents --profile hyper --profile health --profile mission up -d
```

### Docker Compose Profiles

| Profile | Services |
|---------|---------|
| *(none)* | Core infra + observability + MCP server |
| `agents` | All specialist agents |
| `hyper` | Hyper-architect, observer, worker, agent-x |
| `health` | HyperHealth API + worker |
| `mission` | HyperMission API + UI |
| `discord` | Broski Discord bot |

### Security Scanning
```bash
make scan-all
make scan-agent AGENT=healer
make scan-build AGENT=agent-x
make build-secure

# PowerShell — scan ALL 12 agent images
$images = @("hypercode-v24-agent-x","hypercode-v24-broski-bot","hypercode-v24-celery-worker",
             "hypercode-v24-crew-orchestrator","hypercode-v24-healer-agent","hypercode-v24-hyper-architect",
             "hypercode-v24-hyper-observer","hypercode-v24-hyper-worker","hypercode-v24-hypercode-mcp-server",
             "hypercode-v24-test-agent","hypercode-v24-throttle-agent","hypercode-v24-tips-tricks-writer")
foreach ($img in $images) { docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet $img }
```

### Testing
```bash
python -m pytest tests/ --tb=short -q
python -m pytest tests/unit/ -v --tb=short
pytest backend/tests/test_stripe.py -v
```

### Paths (copy-paste ready)
```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4\backend"
cd "H:\HyperAgent-SDK"
cd "H:\the hyper vibe coding hub"
```

### CLI (from H:\HyperAgent-SDK)
```powershell
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100
```

### Stripe Testing (Phase 10F)
```bash
# Test checkout
curl -X POST http://localhost:8000/api/stripe/checkout \
  -H "Content-Type: application/json" \
  -d '{"price_id": "starter", "user_id": "broski_test"}'

# Local webhook testing (Phase 10I)
stripe listen --forward-to localhost:8000/api/stripe/webhook
```

---

## 🧠 Code Conventions

### Python
- **Formatter:** Ruff (`ruff.toml`)
- **Linter:** Pylint (`.pylintrc`) + Ruff
- **Type checker:** Pyright (`pyrightconfig.json`)
- **Test runner:** pytest
- **Python version:** 3.11 in Docker images (3.13+ in devcontainer)
- **Package manager:** pip with `requirements.lock`

### Async Patterns
- All agent communication uses `async/await`
- Redis pub/sub for real-time agent messaging
- FastAPI background tasks for long-running agent jobs

### Agent Naming Conventions
- Agent files: `snake_case.py`
- Agent classes: `PascalCaseAgent`
- Agent endpoints: `/agents/{agent_name}/{action}`

---

## 🚀 MCP Integration

Available MCP tools:
- `mcp__hypercode__hypercode_system_health` — full system health check
- `mcp__hypercode__hypercode_agent_system_health` — agent-specific health
- `mcp__hypercode__hypercode_list_agents` — list all registered agents
- `mcp__hypercode__hypercode_list_tasks` — list active tasks

---

## 🚨 Key Technical Rules (never re-debate these)

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated compat routes
- **Alembic down_revision:** Must match EXACT revision string
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas
- **`.env` files:** Never committed — use Docker secrets in production
- **One bot:** broski-bot. Old Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars, URL-safe
- **GitHub Actions:** Always `--no-cache --pull` in security scanning workflows
- **jaraco.* packages:** Always pin explicitly
- **docker-socket agents** (healer/coder/05-devops): Use `docker-ce-cli` repo, NOT `docker.io`
- **Alembic + create_all:** DB was bootstrapped with `DB_AUTO_CREATE=true` (SQLAlchemy `create_all`). If `alembic_version` table is missing, run `alembic stamp 006` first, then `alembic upgrade head`. Never skip stamp — migrations will try to re-create existing tables.
- **Stripe webhook:** `/api/stripe/webhook` is rate-limit exempt — do NOT add rate limiting
- **Stripe dev mode:** Missing `STRIPE_WEBHOOK_SECRET` = signature check skipped (local only)
- **Conventional commits:** `feat:` `fix:` `docs:` `chore:`
- **Windows PowerShell first**, bash second
- **`apps/web/`:** Archived, never migrate

---

## ⚠️ Known Issues & Gotchas

1. **Windows path handling** — Use `docker-compose.windows.yml` on Windows
2. **Secrets management** — Never commit `.env`; secrets in `./secrets/*.txt`
3. **POSTGRES_PASSWORD** — Plain in `.env` (quoted if special chars). No `POSTGRES_PASSWORD_FILE` alongside.
4. **Agent boot order** — Redis + PostgreSQL must be healthy before agents start
5. **Port conflicts** — Ensure 3000, 3001, 8000, 8008, 8080, 8081, 8088 are free
6. **Test environment** — `fakeredis` used in tests; import via `fakeredis.aioredis`
7. **Volumes wipe** — Alpine trick: `docker run --rm -v "/path":/target alpine sh -c "rm -rf /target/*"`

---

## 🎮 Gamification System

- **BROski$ coins** — earned by completing tasks, agent milestones, commits
- **XP levels** — track developer + system progression
- **Achievements** — unlocked by specific actions in hyper-mission-system
- **Digital Shop:** Prompt Packs (200 BROski$), Templates (150 BROski$), Bonus Lessons (100 BROski$)
- 🏆 Celebrate wins! Every patched CVE = BROski$ earned!

### BROski$ Token Economy
- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata fields

---

## 🔑 Key Dependencies

### Python
- `fastapi` + `uvicorn`, `pydantic`, `redis`/`aioredis`, `sqlalchemy`/`asyncpg`
- `openai`, `anthropic`, `mcp`, `pytest` + `fakeredis`

### Node.js (dashboard)
- `next.js`, `vitest`, TypeScript throughout

---

## 📚 Further Reading

- [README.md](README.md) — Main project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [SECURITY.md](SECURITY.md) — Security policy
- [.claude/](.claude/) — Claude AI config, skills & settings
- [docs/claude-integration/](docs/claude-integration/) — Claude AI integration guide

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
