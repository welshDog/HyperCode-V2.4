# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: April 24, 2026** — update this every session.

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
  - Blast radius shrunk: LLM-generated code can enumerate, can't mutate
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
  - `gen_random_uuid()` + `uuid_generate_v4()` available everywhere
  - Alembic state synced: stamped `008` then `upgrade head` (create_all had left `alembic_version` missing)

### Stripe + Payments
- `POST /api/stripe/checkout` — creates Stripe Checkout Session ✅
- `GET /api/stripe/plans` — lists plans (60s cache) ✅
- `POST /api/stripe/webhook` — signature verified, rate-limit exempt ✅
- Webhook writes: saves payment, awards BROski$, updates subscription tier ✅
- Idempotency: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅
- Token grants: starter=200, builder=800, hyper=2500 ✅

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
- Redis attached to both `data-net` + `agents-net` — fixes agent DNS/connectivity to `redis:6379` ✅ ← **April 24**
- crew-orchestrator now forwards `X-API-Key` to agent `/execute` calls (required by agent auth middleware) ✅ ← **April 24**
- coder-agent ↔ Ollama is end-to-end working with safe fallbacks ✅ ← **April 24**
  - Compose uses `CODER_OLLAMA_MODEL` (prevents global `OLLAMA_MODEL` overrides)
  - Auto-fallback on Ollama errors: missing model / insufficient memory → tries smaller local models
  - Verified success path: `tinyllama:latest`

### April 24 — Agents E2E Smoke Test (Proved the platform is alive)
- Health checks: `GoalKeeper:8050`, `crew-orchestrator:8081`, `mcp-gateway:8820`, `hypercode-core:8000` ✅
- Cross-agent dispatch works (orchestrator → agent `/execute`) ✅
- Ollama reachable from agents via `hypercode-ollama:11434` ✅
- MCP Gateway `/health` returns `200` with an empty body (use `curl -i` to see status) ✅

Smoke flow (PowerShell):
```
curl.exe -s http://127.0.0.1:8050/health
curl.exe -s http://127.0.0.1:8081/health
curl.exe -i http://127.0.0.1:8820/health
curl.exe -s http://127.0.0.1:8000/health

curl.exe -s http://127.0.0.1:11434/api/tags

curl.exe -s -X POST http://127.0.0.1:8081/execute `
  -H "X-API-Key: <ORCHESTRATOR_API_KEY>" `
  -H "Content-Type: application/json" `
  -d '{"task":{"id":"smoke-cross","type":"system_smoke","description":"Ping agents and report status","agents":["frontend-specialist","backend-specialist","database-architect","qa-engineer"],"requires_approval":false}}'

# coder-agent specific (proves Ollama + fallbacks end-to-end)
curl.exe -s -X POST http://127.0.0.1:8081/execute `
  -H "X-API-Key: <ORCHESTRATOR_API_KEY>" `
  -H "Content-Type: application/json" `
  -d '{"task":{"id":"coder-smoke","type":"code_generation","description":"Write hello world in Python.","agents":["coder-agent"],"requires_approval":false}}' | python -c "import json,sys; r=json.load(sys.stdin); print(r.get('status'), r['results']['coder-agent']['result'].get('status'), r['results']['coder-agent']['result'].get('model'))"
```

### Security
- Trivy scanner (`hyper-shield-scanner`) running as container ✅
- GitHub Actions CI — Trivy on every push/PR ✅ (currently **blocked** — GitHub account billing lock, fix on github.com/settings/billing)
- Phase 7–9: Dockerfile hardening, CVE elimination, secrets management ✅
- Stripe keys rotated + scrubbed from 218 commits with `git filter-repo` ✅ ← **April 16**
- OOM crash root cause: Agent X built 30+ images with no memory limit — fixed ✅ ← **April 17**
  - Exit 137 = OOM killed | Exit 128 = SIGTERM under stress (reference for future debugging)
- **Socket-proxy least privilege** ✅ ← **April 19**
  - Main `docker-socket-proxy`: read-only (no POST) — used by coder-agent, agent-x, devops-engineer
  - New `docker-socket-proxy-healer`: CONTAINERS + POST + PING only — used by healer-agent + throttle-agent
  - Reasoning: coder-agent runs LLM-generated code; if compromised it can enumerate only, not restart/kill containers
- **Healer Dockerfile GID fix** ✅ ← **April 19** — `groupadd -o -g 999 docker` (Debian Trixie's appuser system GID collides with 999)
- **GoalKeeper dev API key hardened** — never accepts empty key in dev; only `dev-key` when unset ✅ ← **April 23**
- **Trivy noise fix** — removed vendored `wheel-*.dist-info` from setuptools vendor dir in runtime image ✅ ← **April 23**

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
- `CoursSyncEvent` idempotency guard ✅
- Supabase Edge Function `sync-tokens-to-v24` written ✅ ← **April 16**

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

These need YOU to do them (can't be automated):

- [ ] Register Supabase DB Webhook: `token_transactions` → INSERT → `sync-tokens-to-v24`
- [ ] Set `COURSE_WEBHOOK_SECRET` in both V2.4 `.env` AND Supabase Edge Function env vars
- [ ] Fix frontend hooks: any remaining hardcoded port 8081 → 8000 (Task 4)
- [ ] `VITE_STRIPE_PAYMENT_LINK_URL` — set in `.env.local` + Vercel env vars when ready

---

## 📋 PLANS WRITTEN THIS SESSION (ready to build)

- `HYPERFOCUS_FEATURES_PLAN.md` — 5 neurodivergent features, full prompts inside:
  - Feature 1: Micro-Achievement Git Hook (~2h)
  - Feature 2: HyperSplit Agent (~3h)
  - Feature 3: Session Snapshot Agent (~2h)
  - Feature 4: Morning Briefing `/briefing` (~1.5h)
  - Feature 5: Focus / Panic Mode `make focus` / `make calm` (~1h)
- `BROSKI_PETS_INTEGRATION_PLAN.md` — full BROskiPets × HyperCode plan:
  - Phase 0: Shared infra (1 day)
  - Phase 1: Mint your first pet via BROski$ (3 days)
  - Phase 2: Dev actions → pet XP (1 week)
  - Phase 3: Pet as dev companion, rubber duck mode (2 weeks)
  - Phase 4: On-chain dev portfolio NFT (2 weeks)
  - Phase 5: WelshDogEep graduation reward (3 ever mintable)

---

## 🚀 NEXT UP (in order)

1. **Fix GitHub Actions billing lock** — github.com/settings/billing (Trivy CI blocked until resolved)
2. **`git push origin main`** — 2 commits ready: `d27b67a` (alembic 009) + `8cbc5c9` (security+heal)
3. **E2E checkout test** — `stripe listen --forward-to localhost:8000/api/stripe/webhook` + card `4242 4242 4242 4242`
4. **Gordon Tier 3 verify** — `docker exec celery-worker python -c "from app.core.celery_app import celery_app; print(celery_app.conf.task_acks_late)"` → should print `True`
5. **Token sync smoke test** — manual curl to `/api/v1/economy/award-from-course` with the shared secret
6. **Hyperfocus Features** — start with Feature 1 (git hook, 50 lines, quick win)
7. **BROskiPets Phase 0** — add to docker-compose.agents.yml, verify Ollama shared connection
8. **MERGE_ROADMAP Phase 3** — Agent sandbox access shop item

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:      docker compose --profile ai up -d  (API at http://127.0.0.1:8002)
Tests:           pytest backend/tests -q  (221 passed, 6 skipped — skips are expected)
Prometheus live: monitoring/prometheus/prometheus.yml  (NOT root prometheus.yml)
Redis DB split:  DB 1 = cache  |  DB 2 = rate limits  — never mix
Stripe webhook:  ALWAYS rate-limit exempt — never add limiter to /api/stripe/webhook
Alembic:         if missing alembic_version table → run 'alembic stamp 008' first, then upgrade head
Supabase table:  courses uses price_pence (int) + is_active (bool)
Docker context:  must be 'desktop-linux' on Windows
Memory limits:   ALL services capped in docker-compose.yml — agent-x=1G, core=1.5G, postgres=2G
Pre-build check: make build → auto-runs scripts/pre-build-check.sh (aborts if <15GB free)
OOM exit codes:  137=OOM killed | 128=SIGTERM under stress
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
secrets/                    — Docker secrets (.txt files, gitignored)
docs/GORDON_TIER3.md        — Tier 3 changes + verify commands
docs/DASHBOARD_WEBSOCKETS.md — all 4 WS endpoints + JS examples
docs/PHASE2_TOKEN_SYNC.md   — token sync setup + curl test
```
