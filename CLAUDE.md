# 🧠 HyperCode V2.4 — CLAUDE.md

> **This file is Claude's brain for this project.**
> Read this first. Every session. No exceptions.
> Last updated: May 5, 2026 (evening BST) | Status: 48/48 containers 🟢 | Grade A 🏅 | Phases 0–10Q + BROski Brain COMPLETE ✅

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁥󠁧󠁢󠁷󠁬󠁳󠁿 Builder Context

**Lyndz Williams** (@welshDog) — Llanelli, South Wales  
ADHD + Dyslexia + Autistic brain — hyperfocus mode is a superpower, not a bug ⚡  
Building: The world's first neurodivergent-first autonomous AI infrastructure platform  
**IDE:** Trae IDE (Windows laptop) + Claude Code in terminal  
Verdict from Gordon (Docker AI), April 15 2026:  
> *"You built the future people keep saying they want. You actually did it."*

---

## ⚡ Communication Style (ALWAYS follow this)

- **Short sentences first** — then offer deeper explanation
- **Bullet points + headings** over walls of text
- **Why → How → Ready-to-use example** structure
- **Celebrate wins** — "Nice one BROski♾️!" is correct
- **Remind context** if there's been a pause between messages
- ADHD flow: break into steps, quick wins, no overwhelm
- If Lyndz goes quiet mid-task: check in, don't assume abandon
- **PowerShell first** — Windows laptop primary, WSL2 secondary

---

## 🔒 Sacred Rules (NEVER debate, NEVER change)

```
✔ docker-ce-cli          — NEVER docker.io for socket agents
✔ from app.X import Y    — NEVER from backend.app.X
✔ FastAPI public routes   — BEFORE auth-gated routes
✔ Stripe webhook          — rate-limit EXEMPT, always
✔ data-net + obs-net      — internal: true, never external
✔ .env files              — NEVER committed to git
✔ Commits                 — feat: fix: docs: chore: only
✔ Trivy target            — 0 CRITICAL per image
✔ Import style            — absolute imports, sys.path.insert at top
✔ Python indent           — 4 spaces, NEVER 3, NEVER mixed
✔ Redis DB split          — DB 1 = cache | DB 2 = rate limits, NEVER mix
✔ Stripe webhook path     — NEVER add rate limiter to /api/stripe/webhook
✔ Alembic                 — always check alembic_version table exists first
✔ Docker context          — must be 'desktop-linux' on Windows
✔ WHATS_DONE.md           — update EVERY session, no exceptions
✔ healthcheck             — hypercode-core uses 'localhost' NOT 127.0.0.1 (IPv6 bound)
```

---

## 🛠️ Skills Claude Needs for This Project

### 🐍 Python / FastAPI
- Async FastAPI routes with `asyncpg` + `get_async_db()`
- `@cache_response(ttl=N)` decorator pattern on Redis DB 1
- Rate limiting via `slowapi` on Redis DB 2 (memory:// in tests)
- Circuit breakers via `pybreaker` — 3 active: llm-router, crew-orchestrator, stripe-api
- Pydantic v2 settings via `config.py`
- Alembic migrations — `alembic upgrade head`, stamp 008 if missing

### 🐳 Docker / Compose
- Always: `docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d`
- Memory limits on EVERY service — never add a container without `deploy.resources`
- `make build` → auto-runs `scripts/pre-build-check.sh` — do NOT skip
- Secrets via `.txt` files in `secrets/` — NEVER baked into images
- `docker-ce-cli` repo only for socket agents — NEVER `docker.io`
- Weekly cleanup: `docker system prune -a --filter "until=168h"`
- OOM exit codes: 137=OOM killed | 128=SIGTERM under stress

### 📊 Observability Stack
- Prometheus: `monitoring/prometheus/prometheus.yml` is LIVE — root one is STALE
- Grafana at `:3001`, Tempo traces, Loki logs, Prometheus metrics
- OTLP: `OTLP_EXPORTER_DISABLED=false` = tracing ON (default)
- Hot-reload Prometheus: `curl -X POST localhost:9090/-/reload`

### 🔐 Security
- Trivy: 0 CRITICAL per image — CI runs on every push (currently blocked: billing lock)
- JWT: `validate_security()` rejects weak JWT in prod/staging
- Secrets: `hc_` prefix + `secrets.token_urlsafe(32)` = 43 chars
- Dockerfiles: `python:3.11-slim` + Phase 9 Part A + Part B pattern
- Socket-proxy split: main=read-only, healer proxy=CONTAINERS+POST+PING only

### 💳 Stripe + BROski$ Economy
- Webhook: `POST /api/stripe/webhook` — ALWAYS rate-limit exempt
- Grants: starter=200, builder=800, hyper=2500 BROski$
- Idempotency: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING`
- Token sync: `POST /api/v1/economy/award-from-course` with `X-Sync-Secret` header
- B3 E2E loop PROVED ✅ April 25

### 🤖 Agents
- 25+ agents on `agent-net`
- healer-agent: self-healing closed loop (on obs-net too)
- agent-x: meta-architect (capped at 1G RAM)
- crew-orchestrator: agent lifecycle management
- MCP-GitHub: 26 tools via `mcp-gateway` on `agents-net` ✅
- hyper-split-agent ✅ April 25
- broski-pets-bridge ✅ April 29

### 🧠 BROski Brain (COMPLETE — May 5, 2026)
- **Repo:** `github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne` ✅
- **Path:** `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne`
- Full PARA vault scaffold: 00-Inbox, 01-Projects, 02-Areas, 03-Resources, 04-Archive, Hub
- 4 project notes pre-seeded (HyperCode, HyperAgent, BROskiPets, Hyper-Vibe)
- Dashboard with Dataview live queries, BROski$ Coin Tracker (Level 11)
- Templates: Daily, Project, Task, Morning Briefing
- Focus/Calm/Hyper CSS modes (Level 12)
- GitHub bridge: `scripts/github_to_obsidian.py` syncs 4 repos → vault (Level 9)
- Obsidian Git: auto-commits vault every 10 mins → GitHub (Level 10)
- Docker container: `docker/Dockerfile.github-sync` + compose file (30th container)
- setup.ps1: one-run bootstrap script
- **Levels 9, 10, 11, 12 ALL UNLOCKED** 🎮

### 📦 TypeScript / SDK
- HyperAgent-SDK: `npm: @w3lshdog/hyper-agent@0.1.7`
- CLI commands: `validate`, `registry`, `studio`, `status`, `agents`, `tokens`, `graduate`
- Studio at `http://localhost:4040`
- Path: `H:\HyperAgent-SDK`

### 🗄️ Supabase / Postgres
- Supabase: `courses` table uses `price_pence` (int) + `is_active` (bool)
- NEVER merge Supabase schema with V2.4 Postgres
- RLS enabled: `security_invoker = on` on views
- DB recovery: unix socket = trust auth always works
- Alembic: up to migration 009 (pgcrypto + uuid-ossp)

### 🖥️ Dev Environment
- **IDE:** Trae IDE (Windows laptop) — visual editing, autocomplete, MCP hooks
- **Agent work:** Claude Code in terminal — autonomous tasks, reads CLAUDE.md
- **Trae Pro:** expired May 2026 — using Claude Code this month
- **Primary:** Windows PowerShell | **Secondary:** WSL2
- **Docker context:** must be `desktop-linux` on Windows

---

## 📊 System Status (May 5, 2026)

| Metric | Value |
|---|---|
| Containers | 48 running (post-cleanup) 🟢 |
| Tests | 223 passed, 6 skipped ✅ |
| E2E shop-purchase test | ✅ PASSING |
| Prometheus targets | 7/7 UP ✅ |
| OTLP traces | LIVE in Tempo ✅ |
| Circuit breakers | 3 active — all CLOSED ✅ |
| Docker AI grade | A 🏅 |
| Commits | 700+ |
| Services | 57 |
| Agents | 25+ |
| BROski Brain | ✅ COMPLETE — May 5 🧠 |
| HyperFocus Features | ✅ ALL 5 DONE |
| Security headers | 6/6 ✅ (frontend/vercel.json) |
| /welcome page | ✅ LIVE on Vercel |

---

## 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0–6 | Identity, tokens, agents, shop, observability, CLI | ✅ ALL DONE |
| 7–9 | Security hardening, Trivy CI, CVE elimination | ✅ ALL DONE |
| 10A–10E | FastAPI, networks, secrets, auth, WS | ✅ ALL DONE |
| 10F–10K | Stripe full stack + BROski$ tokens | ✅ ALL DONE |
| 10L | Healthchecks — all 29 containers | ✅ April 15 |
| 10M | Gordon Tier 1 — Prometheus 7/7 UP | ✅ April 15 |
| 10N | Gordon Tier 2 — ALL 4 STEPS | ✅ April 16 🏆 |
| 10O | Course → Stripe frontend wired | ✅ April 16 💳 |
| 10P | DB Recovery + Secrets Armed | ✅ April 18 🔧 |
| 10Q | Security Hardening + Monitoring + Migration 009 | ✅ April 19 🔒 |
| 10R | Gordon Tier 3 + Referral + Docker Cleanup | ✅ May 3 |
| 10S | HyperFocus Features ALL 5 + Pets + HyperSplit | ✅ April 25–29 |
| **10T** | **BROski Brain — Obsidian + HyperFocus z0ne** | ✅ **May 5, 2026 🧠** |

---

## 🚀 NEXT UP — Phase 10U onwards

1. **First student invite** — `/welcome` is green 🎓
2. **E2E checkout test** — `stripe listen` + card `4242 4242 4242 4242`
3. **BROskiPets Phase 1** — mint first pet via BROski$
4. **HyperAgent-SDK Phase 2** — npm 0.2.0
5. **Fix GitHub Actions billing lock** — github.com/settings/billing
6. **Level 13** — Morning Briefing live
7. **Level 14** — GitHub Webhooks real-time
8. **Level 15** — HyperAgent AI Daily Briefing
9. **`env_file` tech debt** — add `env_file: .env` to `hypercode-core` in compose
10. **prometheus.yml tidy** — delete stale root one

---

## 🏗️ Architecture Quick Ref

```
Networks:
  app-net     → core services (internal)
  data-net    → redis, postgres, chroma, minio (internal)
  obs-net     → prometheus, grafana, loki, tempo (internal)
  agent-net   → all agents

Key ports:
  8000  hypercode-core API
  8002  hypercode-ai API (profile: ai)
  8081  crew-orchestrator
  8088  hypercode-dashboard
  8095  hyperhealth-api
  8098  broski-pets-bridge
  9090  prometheus
  3001  grafana
  3100  loki
  3200  tempo
  6379  redis
  5432  postgres
```

---

## 📌 Known Issues (fix as we go)

| Issue | Fix | Priority |
|---|---|---|
| `env_file` missing on `hypercode-core` | Add `env_file: .env` to service block | 🔴 HIGH |
| Stripe webhook secret stale | `supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...` → redeploy | 🔴 HIGH |
| GitHub Actions billing lock | github.com/settings/billing | 🔴 HIGH |
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟡 MED |
| `throttle-agent` not started | `docker compose --profile agents up -d throttle-agent` | 🟡 LOW |
| `loki` no healthcheck | Add `curl -f http://localhost:3100/ready` | 🟡 LOW |
| Root `prometheus.yml` stale | Delete/archive — use `monitoring/prometheus/` | 🟡 LOW |
| Anthropic credits exhausted | Top up console.anthropic.com/billing — Perplexity fallback working | 🟡 TOP UP |

---

## 📦 Key Files Claude Should Know

```
docker-compose.yml              — main stack (65 services)
docker-compose.secrets.yml      — secrets injection (ALWAYS alongside main)
backend/app/main.py             — FastAPI core app
frontend/vercel.json            — Vercel config + security headers ✅
frontend/src/pages/Welcome.tsx  — hero onboarding page (LIVE)
scripts/Test-ShopPurchase.ps1   — E2E shop-purchase test
monitoring/prometheus/          — LIVE Prometheus config
agents/                         — all agent code
healer-agent/                   — self-healing logic
CLAUDE_CONTEXT.md               — extended project context
WHATS_DONE.md                   — always update this each session
docs/INDEX.md                   — master docs navigation
HYPER_ECOSYSTEM_PLAN_MAY4.md    — 4-repo master plan
```

---

## 🧪 Testing Commands

```powershell
# Health checks:
curl http://localhost:8000/health
curl http://localhost:8081/health
curl http://localhost:8095/health
curl http://localhost:8098/health  # broski-pets

# Run tests:
pytest backend/tests -q  # 223 passed, 6 skipped
pytest backend/tests/test_stripe.py -v

# E2E shop-purchase:
pwsh scripts/Test-ShopPurchase.ps1

# Docker status:
docker compose ps
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr -v "healthy"

# Start everything:
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
docker compose --profile ai up -d      # AI backend
docker compose --profile discord up -d broski-bot

# Focus modes:
make focus   # stops 14 non-essential containers + 25-min timer
make calm    # restores all + awards 75 BROski$

# Weekly Docker cleanup:
docker system prune -a --filter "until=168h"

# Prometheus hot-reload:
curl -X POST localhost:9090/-/reload

# Circuit breakers:
curl localhost:8000/api/v1/health | jq .circuit_breakers

# GitHub Brain sync:
python scripts/github_to_obsidian.py  # needs GITHUB_PAT env var
```

---

## 🏆 Achievements Unlocked

- ✅ Gordon Docker AI: **Grade A** — *"world-class infrastructure"*
- ✅ 48/48 containers healthy (post-cleanup May 3)
- ✅ Self-healing closed loop (Healer → Prometheus → Alertmanager → recovery)
- ✅ Neurodivergent-first design recognised as *rare* by Docker AI
- ✅ Gordon Tier 1 + Tier 2 + Tier 3 ALL COMPLETE
- ✅ Course → Stripe → BROski$ live + E2E proved
- ✅ All 5 HyperFocus Features SHIPPED
- ✅ MCP-GitHub LIVE — 26 tools
- ✅ BROskiPets bridge LIVE + Cosmic Dragon minted
- ✅ Referral system live (BRO-codes)
- ✅ /welcome hero onboarding LIVE on Vercel
- ✅ Security headers 6/6 fixed (frontend/vercel.json)
- ✅ **BROski Brain COMPLETE** 🧠 — May 5, 2026
- ✅ **Levels 9, 10, 11, 12 ALL UNLOCKED** 🎮

---

## 👋 For New Claude Sessions

Hey Claude! Working with Lyndz Williams (@welshDog) on HyperCode V2.4.

1. **Read this file first** — especially Sacred Rules + Skills section
2. **Check CLAUDE_CONTEXT.md** — phase source of truth
3. **Check WHATS_DONE.md** — never suggest something already built
4. **Current phase: 10T done** → next = 10U (student invite + checkout test + Pets Phase 1)
5. **IDE:** Trae IDE (Windows) — visual. Claude Code terminal — autonomous tasks.
6. **Trae Pro expired May 2026** — Claude Code is the agent brain this month
7. **223 tests green**, 48 containers, BROski Brain live, all 5 HyperFocus features done
8. **3 red issues:** env_file tech debt | Stripe webhook secret stale | GitHub billing lock
9. **Style:** Short. Friendly. BROski energy. Celebrate wins. 🏆
10. **Never:** Wall of text. Never debate Sacred Rules.

> *"You built the future people keep saying they want. You actually did it." — Gordon, Docker AI*

🏴󠁧󠁢󠁷󠁬󠁳󠁿 Let's build it.
