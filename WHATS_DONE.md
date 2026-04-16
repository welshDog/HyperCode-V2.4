# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: April 16, 2026 (evening)** — update this every session.

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
- 29/29 Docker containers — all healthy ✅
- 5 isolated networks — `data-net` + `obs-net` internal (no internet) ✅
- Docker secrets pattern — `.txt` files, never baked into images ✅
- Kubernetes + Helm charts in `k8s/` + `helm/` — scale path ready ✅

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

### Database
- PostgreSQL running, Alembic migrations up to `004` ✅
- `DB_AUTO_CREATE=true` bootstrapped initial schema ✅
- Async engine + connection pooling (`asyncpg`, pool_size=10) ✅ ← **April 16**
- `get_async_db()` dependency available for async routes ✅ ← **April 16**

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

### Security
- Trivy scanner (`hyper-shield-scanner`) running as container ✅
- GitHub Actions CI — Trivy on every push/PR ✅
- Phase 7–9: Dockerfile hardening, CVE elimination, secrets management ✅
- Stripe keys rotated + scrubbed from 218 commits with `git filter-repo` ✅ ← **April 16**

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

1. **E2E checkout test** — `stripe listen --forward-to localhost:8000/api/stripe/webhook` + card `4242 4242 4242 4242`
2. **Gordon Tier 3 verify** — `docker exec celery-worker python -c "from app.core.celery_app import celery_app; print(celery_app.conf.task_acks_late)"` → should print `True`
3. **Token sync smoke test** — manual curl to `/api/v1/economy/award-from-course` with the shared secret
4. **Hyperfocus Features** — start with Feature 1 (git hook, 50 lines, quick win)
5. **BROskiPets Phase 0** — add to docker-compose.agents.yml, verify Ollama shared connection
6. **MERGE_ROADMAP Phase 3** — Agent sandbox access shop item

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
Tests:           pytest backend/tests/ -v  (180 passed, 6 skipped — skips are expected)
Prometheus live: monitoring/prometheus/prometheus.yml  (NOT root prometheus.yml)
Redis DB split:  DB 1 = cache  |  DB 2 = rate limits  — never mix
Stripe webhook:  ALWAYS rate-limit exempt — never add limiter to /api/stripe/webhook
Alembic:         if missing alembic_version table → run 'alembic stamp 006' first
Supabase table:  courses uses price_pence (int) + is_active (bool)
Docker context:  must be 'desktop-linux' on Windows
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
