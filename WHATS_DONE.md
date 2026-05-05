# ✅ WHATS_DONE.md — HyperCode Ecosystem
> One file. Short bullets. No walls of text.
> **Updated: May 5, 2026** — update this every session.

---

## 🏗️ THE 5 REPOS

| Repo | What it is | Where |
|---|---|---|
| HyperCode-V2.4 | Main platform — Docker, FastAPI, agents, infra | `H:\HyperStation zone\HyperCode\HyperCode-V2.4` |
| HyperAgent-SDK | TypeScript SDK — agent spec, CLI, templates | `H:\HyperAgent-SDK` |
| Hyper-Vibe-Coding-Course | Course frontend + Supabase + token shop | `H:\Hyper-Vibe-Coding-Course` |
| BROskiPets-LLM-dNFT | Pet NFT system — LLM + on-chain | `github.com/welshDog/BROskiPets-LLM-dNFT` |
| BROski-Obsidian-Brain | Second Brain vault — Obsidian + GitHub bridge | `H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne` ← **NEW May 5** |

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
- **healthcheck IPv6 fix** — `hypercode-core` healthcheck changed from `127.0.0.1` → `localhost` (Uvicorn binds `[::]` IPv6, not IPv4) ✅ ← **May 4**

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

### BROski$ Token Economy
- `public.users.broski_tokens` balance column ✅
- `token_transactions` — append-only ledger ✅
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only ✅
- `CourseSyncEvent` model + migration 004 — idempotency for cross-repo sync ✅
- **BROski$ Obsidian Coin Tracker LIVE** ✅ ← **May 5** (Dataview widget in Dashboard, Level 11)

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
- **`/welcome` page verified LIVE** ✅ ← **May 4**
- **Dev command:** `npm run dev:frontend` (NOT `npm run dev`) ✅ ← **May 4**

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
- **hyper-split-agent** ✅ ← **April 25**
- **sys.path import fix** ✅ ← **April 26**
- **hypersplit import bug fixed** ✅ ← **April 26**
- **broski-pets-bridge LIVE** ✅ ← **April 29**

### 🏆 Hyperfocus Features — ALL 5 DONE
- **Feature 1: Micro-Achievement Git Hook** ✅ April 25
- **Feature 2: HyperSplit Agent** ✅ April 25
- **Feature 3: Session Snapshot Agent** ✅ April 25
- **Feature 4: Morning Briefing `/briefing`** ✅ April 26
- **Feature 5: Focus / Panic Mode** ✅ April 26

### 🧠 BROski Brain (Second Brain) — NEW May 5
- **Repo:** `github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne` ✅ ← **May 5**
- **Vault scaffold** — full PARA structure (00-Inbox, 01-Projects, 02-Areas, 03-Resources, 04-Archive, Hub) ✅
- **4 project notes pre-seeded** — HyperCode, HyperAgent, BROskiPets, Hyper-Vibe ✅
- **Dashboard** — Dataview live queries: active projects, BROski$, GitHub issues, recent wins ✅
- **Templates** — Daily, Project, Task, Morning Briefing ✅
- **BROski$ Coin Tracker** — Dataview widget + economy table ✅ (Level 11)
- **Focus/Calm/Hyper CSS modes** — one keypress toggle ✅ (Level 12)
- **GitHub bridge LIVE** — `scripts/github_to_obsidian.py` syncs 4 repos → vault ✅ (Level 9)
- **Obsidian Git** — auto-commits vault every 10 mins → GitHub ✅ (Level 10)
- **Docker container** — `docker/Dockerfile.github-sync` + compose file ready (30th container) ✅
- **setup.ps1** — one-run bootstrap script ✅

### Security
- Trivy scanner (`hyper-shield-scanner`) running ✅
- GitHub Actions CI — Trivy on every push/PR ✅ (currently **blocked** — billing lock)
- Phase 7–9: Dockerfile hardening, CVE elimination, secrets management ✅
- Stripe keys rotated + scrubbed from 218 commits ✅ ← **April 16**
- **Socket-proxy least privilege** ✅ ← **April 19**

### Celery
- Celery + Redis task queue running ✅
- `task_acks_late=True` ✅ ← **April 16**
- `worker_prefetch_multiplier=1` ✅ ← **April 16**
- `run_agent_task` with exponential backoff retry ✅ ← **April 16**

### HyperAgent-SDK
- `hyper-agent-spec.json` — JSON Schema contract ✅
- CLI: `validate`, `registry`, `studio`, `status`, `agents`, `tokens`, `graduate` ✅
- Studio at `http://localhost:4040` ✅
- Published to npm: `@w3lshdog/hyper-agent@0.1.7` ✅
- GitHub Actions CI — `npm test` on every push + PR ✅

### Phase 2 Token Sync (Course ↔ V2.4)
- V2.4 endpoint `POST /api/v1/economy/award-from-course` ✅
- `X-Sync-Secret` header auth ✅
- `CourseSyncEvent` idempotency guard ✅
- Supabase Edge Function `sync-tokens-to-v24` written ✅ ← **April 16**

---

## 🧹 APRIL 29 — PHASE 1 TRIAGE SESSION
- Closed stale issue #83 ✅
- Merged 5 Dependabot PRs — 0 open remaining ✅
- broski-pets-bridge all 4 health checks green ✅

---

## 🐾 APRIL 29 — PHASE 3 PETS (COSMIC DRAGON)
- Docker DNS fixed for pets bridge ✅
- IDOR hardened on pets endpoints ✅
- Cosmic Dragon minted + leaderboard live ✅
- XP confirmed: 0→10, streak day 1 ✅

---

## 📋 MAY 4 — MASTER PLAN REFRESH
- `HYPER_ECOSYSTEM_PLAN_MAY4.md` shipped ✅
- `CLAUDE.md` updated — 4th repo added ✅
- `/welcome` page LIVE ✅

---

## 🧠 MAY 5 — BROSKI BRAIN LAUNCH
- BROski-Obsidian-Brain repo created + full scaffold pushed ✅
- GitHub bridge script live — 4 repos syncing ✅
- Obsidian Git — vault auto-backup every 10 mins ✅
- BROski$ Coin Tracker — Dataview widget live ✅
- Focus/Calm/Hyper CSS modes — all 3 tested ✅
- **Levels 9, 10, 11, 12 ALL UNLOCKED** 🎮 ✅

---

## 🔧 ONE-TIME MANUAL STEPS REMAINING

- [ ] Register Supabase DB Webhook: `token_transactions` → INSERT → `sync-tokens-to-v24`
- [ ] Set `COURSE_WEBHOOK_SECRET` in both V2.4 `.env` AND Supabase Edge Function env vars
- [ ] Fix frontend hooks: any remaining hardcoded port 8081 → 8000
- [ ] `VITE_STRIPE_PAYMENT_LINK_URL` — set in `.env.local` + Vercel env vars
- [ ] Add `DISCORD_USER_ID=<your_id>` to `.env` so `make calm` awards tokens correctly
- [ ] Fix GitHub Actions billing lock — github.com/settings/billing
- [ ] Add `env_file: .env` to `hypercode-core` in `docker-compose.yml`
- [ ] Add `GITHUB_PAT` to HyperCode-V2.4 `.env` + spin up `github-sync` Docker container (Level 9 persistent)

---

## 🚀 NEXT UP (in order)

1. **First student invite** — `/welcome` is green 🎓
2. **E2E checkout test** — card `4242 4242 4242 4242`
3. **BROskiPets Phase 1** — mint first pet via BROski$
4. **HyperAgent-SDK Phase 2** — npm 0.2.0
5. **Fix GitHub Actions billing lock**
6. **Level 13** — Morning Briefing live
7. **Level 14** — GitHub Webhooks real-time
8. **Level 15** — HyperAgent AI Daily Briefing

---

## 🔑 KEY FACTS (never re-look-up)

```
Start command:   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
AI backend:      docker compose --profile ai up -d
Discord bot:     docker compose --profile discord up -d broski-bot
Tests:           pytest backend/tests -q  (223 passed, 6 skipped)
Prometheus live: monitoring/prometheus/prometheus.yml
Redis DB split:  DB 1 = cache  |  DB 2 = rate limits
Stripe webhook:  ALWAYS rate-limit exempt
Alembic:         if missing alembic_version → 'alembic stamp 008' then upgrade head
Supabase table:  courses uses price_pence (int) + is_active (bool)
Docker context:  must be 'desktop-linux' on Windows
Memory limits:   ALL services capped — agent-x=1G, core=1.5G, postgres=2G
Pre-build check: make build → auto-runs pre-build-check.sh
make focus:      stops 14 non-essential containers + 25-min timer
make calm:       restores all + awards 75 BROski$
broski-pets:     health → http://localhost:8098/health
Course path:     H:\Hyper-Vibe-Coding-Course
Course dev:      npm run dev:frontend
healthcheck fix: hypercode-core uses localhost not 127.0.0.1
Brain repo:      H:\BROski-Obsidian-Brain-for-HyperFocus-z0ne
Brain vault:     HYPERFOCUS_ZONE/ folder inside brain repo
GitHub sync:     python scripts/github_to_obsidian.py (needs GITHUB_PAT env var)
Obsidian Git:    auto-commits vault every 10 mins to brain repo
```

---

## 📁 WHERE THINGS LIVE

```
docker-compose.yml                    — main stack
docker-compose.secrets.yml            — secrets injection
backend/app/main.py                   — FastAPI core
backend/app/core/config.py            — all settings
monitoring/prometheus/                — live Prometheus config
agents/                               — all agent code
secrets/                              — Docker secrets (.txt files, gitignored)
HYPER_ECOSYSTEM_PLAN_MAY4.md         — 4-repo master plan
BROski-Obsidian-Brain/scripts/        — github_to_obsidian.py + setup.ps1
BROski-Obsidian-Brain/docker/         — Dockerfile.github-sync + compose
```
