# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: April 29, 2026** — update this every session.

---

## 🏗️ THE 3 REPOS

| Repo | What it is | Where |
|---|---|---|
| HyperCode-V2.4 | Main platform — Docker, FastAPI, agents, infra | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| HyperAgent-SDK | TypeScript SDK — agent spec, CLI, templates | `H:\HyperAgent-SDK` |
| Hyper-Vibe-Coding-Course | Course frontend + Supabase + token shop | `H:\the hyper vibe coding hub` |

---

## ✅ BUILT AND WORKING

### Infrastructure
- 32/32 Docker containers — all healthy ✅ ← **April 19** (HyperHealth API live)
- 5 isolated networks — `data-net` + `obs-net` internal (no internet) ✅
- Docker secrets pattern — `.txt` files, never baked into images ✅
- Kubernetes + Helm charts in `k8s/` + `helm/` — scale path ready ✅
- **Memory limits on ALL services** — every container capped, OOM cascades impossible ✅ ← **April 17**
  - agent-x hard-capped at 1G RAM (was unlimited — caused OOM crash April 17)
  - healer, alertmanager, hyper-agents, all specialists, all infra — all capped
- `scripts/pre-build-check.sh` — disk + memory guard before any Docker build ✅ ← **April 17**
  - `make build` now runs it automatically — aborts if <15GB free
- **OOM recovery completed April 17** — 34.4GB freed, 24/24 containers restored ✅
- **Socket-proxy split** — main proxy read-only (coder-agent etc.), new `docker-socket-proxy-healer` with CONTAINERS+POST+PING for healer/throttle-agent only ✅ ← **April 19**
- **Healer on obs-net** — can now reach Grafana/Prometheus for diagnostics ✅ ← **April 19**

### Observability
- Prometheus 7/7 targets UP — `monitoring/prometheus/prometheus.yml` is the live config ✅
- Grafana at `:3001` — all data flowing ✅
- OTLP traces live in Tempo — `localhost:3001 → Explore → Tempo` ✅
- Loki + Promtail — log aggregation running ✅

### Backend (FastAPI — hypercode-core)
- `/metrics` Prometheus endpoint ✅
- `/health` with Redis cache (10s TTL) ✅
- Rate limiting — Redis DB 2, Stripe webhook exempt ✅
- Redis caching (`@cache_response`) — DB 1 ✅
- Circuit breakers — 3 active: `llm-router`, `crew-orchestrator`, `stripe-api` ✅
- CORS via `settings.parsed_cors_allow_origins()` ✅
- Security headers middleware ✅
- HTTP metrics middleware — req count, response times, error rate → Redis ✅
- `validate_security()` — rejects weak JWT in prod/staging ✅
- **Core deps split for security** — `backend/requirements.txt` = core only, `backend/requirements-ai.txt` = optional AI deps ✅ ← **April 23**
- **AI backend profile** — `docker compose --profile ai up -d` runs `ai-backend` with `INSTALL_AI_DEPS=true` ✅ ← **April 23**
- Core RAG boot no longer hard-requires `langchain_text_splitters` (optional import + fallback chunker) ✅ ← **April 24**

### Database
- PostgreSQL running, Alembic migrations up to `009` ✅ ← **April 19**
- `DB_AUTO_CREATE=true` bootstrapped initial schema ✅
- Async engine + connection pooling (`asyncpg`, pool_size=10) ✅ ← **April 16**
- `get_async_db()` dependency available for async routes ✅ ← **April 16**
- Migration 009 — `pgcrypto` + `uuid-ossp` extensions enabled ✅ ← **April 19**

### Stripe + Payments
- `POST /api/stripe/checkout` — creates Stripe Checkout Session ✅
- `GET /api/stripe/plans` — lists plans (60s cache) ✅
- `POST /api/stripe/webhook` — signature verified, rate-limit exempt ✅
- Webhook writes: saves payment, awards BROski$, updates subscription tier ✅
- Idempotency: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅
- Token grants: starter=200, builder=800, hyper=2500 ✅
- **B3 E2E Stripe loop PROVED** ✅ ← **April 25**
  - Stripe listener → `http://127.0.0.1:8000/api/stripe/webhook` (IPv4 — IPv6 issue avoided)
  - `checkout.session.completed` → writes `public.payments` row + `public.token_transactions` row
  - `broski_tokens` balance increases by +200 on `starter` plan purchase
  - Webhook secret refreshed per listener session ✅

### BROski$ Token Economy
- `public.users.broski_tokens` balance column ✅
- `token_transactions` — append-only ledger ✅
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only ✅
- `CourseSyncEvent` model + migration 004 — idempotency for cross-repo sync ✅

### Course Frontend (Hyper-Vibe)
- `/pricing` → Stripe checkout → `/payment-success` → enrolled ✅
- `PaymentSuccess.tsx` — handles per-course AND subscription flows ✅
- Dashboard — BROski$ balance card ✅
- TokensPage — wired to checkout API ✅
- Certificates feature ✅
- Quiz/exercise system ✅
- Referral system ✅
- 7 courses seeded in Supabase (`price_pence`, `is_active`) ✅
- RLS enabled — `security_invoker = on` on views ✅

### WebSocket Endpoints (V2.4)
- `/ws/uplink` — CognitiveUplink (Phase 10J) ✅
- `/ws/agents` + `GET /api/v1/agents/status` — agent heartbeats ✅
- `/ws/events` + `GET /api/v1/events` SSE — live event stream ✅
- `/ws/logs` + `GET /api/v1/logs` — live log stream ✅

### Agents (25+)
- healer-agent — self-healing, monitors + auto-recovers ✅
- agent-x — meta-architect ✅
- crew-orchestrator — agent lifecycle ✅
- hyper-architect, hyper-observer, hyper-worker ✅
- super-hyper-broski-agent, broski-bot ✅
- Redis attached to both `data-net` + `agents-net` ✅ ← **April 24**
- crew-orchestrator now forwards `X-API-Key` to agent `/execute` calls ✅ ← **April 24**
- coder-agent ↔ Ollama is end-to-end working with safe fallbacks ✅ ← **April 24**
- **hyper-split-agent** ✅ ← **April 25** (Feature 2 DONE)
- **sys.path import fix** ✅ ← **April 26**
- **hypersplit import bug fixed** ✅ ← **April 26**
- **broski-pets-bridge LIVE** ✅ ← **April 29**
  - `pets_enabled:true`, `ollama_connected:true`, `redis_connected:true`, `mcp_connected:true`
  - MCP gateway port fixed (8099→8820), stale `.env` entry cleaned
  - Health endpoint: `http://localhost:8098/health`

### 🏆 Hyperfocus Features — ALL 5 DONE
- **Feature 1: Micro-Achievement Git Hook** ✅ April 25
  - `scripts/git-hooks/post-commit` + `scripts/install-git-hooks.ps1`
  - Awards tokens via `POST /api/v1/economy/award-from-course` (idempotent)
  - Commit-type awards: `fix:` = 25, `docs:` = 5, fallback = 10
- **Feature 2: HyperSplit Agent** ✅ April 25
  - `agents/hyper-split-agent/` — FastAPI on port 8096
  - `POST /api/v1/hypersplit` — proxied through hypercode-core
- **Feature 3: Session Snapshot Agent** ✅ April 25
  - `agents/session-snapshot/` — FastAPI on port 8097
  - `make snapshot` writes `SESSION.md` (gitignored)
  - `make up` / `make start` / `make agents` prints SESSION.md automatically
- **Feature 4: Morning Briefing `/briefing`** ✅ April 26
  - `agents/broski-bot/src/cogs/briefing.py` — Discord slash command
  - Pulls: stack health + BROski$ balance + Pulse + Next Up + last git commit
  - Output: single clean Discord embed
- **Feature 5: Focus / Panic Mode** ✅ April 26
  - `scripts/focus-mode.sh` — stops 14 non-essential containers + 25-min bg timer
  - `scripts/calm-mode.sh` — restores all containers + awards 75 BROski$ (if >10 min)
  - `make focus` / `make calm` in Makefile ✔️
  - `.focus_session_start` in `.gitignore` ✔️
  - Token award via `POST /api/v1/broski/award` (graceful fallback if core offline)

### Security
- Trivy scanner (`hyper-shield-scanner`) running as container ✅
- GitHub Actions CI — Trivy on every push/PR ✅ (currently **blocked** — GitHub account billing lock, fix on github.com/settings/billing)
- Phase 7–9: Dockerfile hardening, CVE elimination, secrets management ✅
- Stripe keys rotated + scrubbed from 218 commits with `git filter-repo` ✅ ← **April 16**
- **Socket-proxy least privilege** ✅ ← **April 19**
- **GoalKeeper dev API key hardened** ✅ ← **April 23**
- **Trivy noise fix** ✅ ← **April 23**

### Celery
- Celery + Redis task queue running ✅
- `task_acks_late=True` — tasks re-queue on worker crash ✅ ← **April 16**
- `worker_prefetch_multiplier=1` — no task starvation ✅ ← **April 16**
- `run_agent_task` with exponential backoff retry ✅ ← **April 16**

### HyperAgent-SDK
- `hyper-agent-spec.json` — JSON Schema contract, shared across all 3 repos ✅
- CLI: `validate`, `registry`, `studio`, `status`, `agents`, `tokens`, `graduate` ✅
- Studio at `http://localhost:4040` ✅
- Published to npm: `@w3lshdog/hyper-agent@0.1.7` ✅
- GitHub Actions CI — `npm test` on every push + PR ✅ ← **April 16**

### Phase 2 Token Sync (Course ↔ V2.4)
- V2.4 endpoint `POST /api/v1/economy/award-from-course` ✅
- `X-Sync-Secret` header auth (constant-time compare) ✅
- `CourseSyncEvent` idempotency guard ✅
- Supabase Edge Function `sync-tokens-to-v24` written ✅ ← **April 16**

---

## 🧹 APRIL 29 — PHASE 1 TRIAGE SESSION

- Closed stale issue #83 (Phase 10D + 10H — confirmed shipped) ✅
- Merged Dependabot PR #183 — prometheus-client ≥0.25.0 (crew-orchestrator) ✅
- Merged Dependabot PR #184 — express-rate-limit 8.3.2→8.4.1 (hyper-mission-system) ✅
- Merged Dependabot PR #189 — redis 5.10.0→5.12.1 (hyper-mission-system) ✅
- Merged Dependabot PR #182 — fastapi 0.109→0.136 (crew-orchestrator) ✅
- Merged Dependabot PR #180 — langchain-openai 1.2→1.2.1 (crew-orchestrator) ✅
- **0 open Dependabot PRs remaining** — full queue cleared ✅
- Enabled `BROSKIE_PETS_ENABLED=true` in `.env` ✅
- Fixed MCP gateway port mismatch: `MCP_GATEWAY_URL` was `8099`, corrected to `8820` ✅
- Cleaned stale duplicate `.env` entry (old 8099 line removed) ✅
- broski-pets-bridge all 4 health checks green: `pets_enabled` + `ollama` + `redis` + `mcp` ✅

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

These need YOU to do them (can't be automated):

- [ ] Register Supabase DB Webhook: `token_transactions` → INSERT → `sync-tokens-to-v24`
- [ ] Set `COURSE_WEBHOOK_SECRET` in both V2.4 `.env` AND Supabase Edge Function env vars
- [ ] Fix frontend hooks: any remaining hardcoded port 8081 → 8000 (Task 4)
- [ ] `VITE_STRIPE_PAYMENT_LINK_URL` — set in `.env.local` + Vercel env vars when ready
- [ ] Add `DISCORD_USER_ID=<your_id>` to `.env` so `make calm` awards tokens to the right account

---

## 📋 PLANS WRITTEN / IN PROGRESS

- `HYPERFOCUS_FEATURES_PLAN.md` — 5 neurodivergent features: **ALL ✅ DONE April 25–26**
- `BROSKI_PETS_INTEGRATION_PLAN.md` — full BROskiPets × HyperCode plan:
  - Phase 0: Shared infra (1 day)
  - Phase 1: Mint your first pet via BROski$ (3 days)
  - Phase 2: Dev actions → pet XP (1 week)
  - Phase 3: Pet as dev companion, rubber duck mode (2 weeks)
  - Phase 4: On-chain dev portfolio NFT (2 weeks)
  - Phase 5: WelshDogEep graduation reward (3 ever mintable)

---

## 🚀 NEXT UP (in order)

1. **Blockers B1-B3** — Supabase DB webhook + Edge Function secrets + Stripe E2E re-verify
2. **HyperAgent-SDK Phase 2** — validator UX improvements, Python + TypeScript starter templates, npm 0.2.0
3. **Hyper-Vibe-Coding-Course** — move over, review current state, plan next features
4. **Fix GitHub Actions billing lock** — github.com/settings/billing (Trivy CI blocked until resolved)
5. **BROskiPets Phase 1** — mint first pet via BROski$ (bridge is live and healthy ✅)
6. **MERGE_ROADMAP Phase 3** — Agent sandbox access shop item

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:      docker compose --profile ai up -d  (API at http://127.0.0.1:8002)
Discord bot:     docker compose --profile discord up -d broski-bot
Tests:           pytest backend/tests -q  (223 passed, 6 skipped — skips are expected)
Agent tests:     crew-orchestrator: 15p | session-snapshot: 3p | hyperhealth: 12p
Prometheus live: monitoring/prometheus/prometheus.yml  (NOT root prometheus.yml)
Redis DB split:  DB 1 = cache  |  DB 2 = rate limits  — never mix
Stripe webhook:  ALWAYS rate-limit exempt — never add limiter to /api/stripe/webhook
HyperSplit:      POST /api/v1/hypersplit (auth) → proxies to hyper-split-agent:8096
Alembic:         if missing alembic_version table → run 'alembic stamp 008' first, then upgrade head
Supabase table:  courses uses price_pence (int) + is_active (bool)
Docker context:  must be 'desktop-linux' on Windows
Memory limits:   ALL services capped in docker-compose.yml — agent-x=1G, core=1.5G, postgres=2G
Pre-build check: make build → auto-runs scripts/pre-build-check.sh (aborts if <15GB free)
OOM exit codes:  137=OOM killed | 128=SIGTERM under stress
sys.path fix:    session-snapshot, hyperhealth, crew-orchestrator all use safe sibling-import bootstrap
/briefing:       pulls health + BROski$ + pulse + WHATS_DONE next + last git commit → Discord embed
make focus:      stops 14 non-essential containers + 25-min bg timer
make calm:       restores all + awards 75 BROski$ if session >10 mins
broski-pets:     health → http://localhost:8098/health | MCP gateway → http://mcp-gateway:8820
```

---

## 📁 WHERE THINGS LIVE

```
docker-compose.yml          — main stack (all 65 services)
docker-compose.secrets.yml  — secrets injection (always use alongside main)
backend/app/main.py         — FastAPI core (routes, middleware, startup)
backend/app/core/config.py  — all settings
monitoring/prometheus/      — live Prometheus config
agents/                     — all agent code
agents/hyper-split-agent/   — HyperSplit Agent (Feature 2)
agents/session-snapshot/    — Session Snapshot Agent (Feature 3)
agents/hyperhealth/         — HyperHealth API + worker
agents/crew-orchestrator/   — Central task orchestrator
agents/broski-bot/          — Discord bot (Feature 4: /briefing)
agents/broski-pets-bridge/  — BROski Pets bridge (port 8098) ← April 29
scripts/focus-mode.sh       — Focus Mode (Feature 5)
scripts/calm-mode.sh        — Calm Mode (Feature 5)
secrets/                    — Docker secrets (.txt files, gitignored)
docs/GORDON_TIER3.md        — Tier 3 changes + verify commands
docs/DASHBOARD_WEBSOCKETS.md — all 4 WS endpoints + JS examples
docs/PHASE2_TOKEN_SYNC.md   — token sync setup + curl test
```
