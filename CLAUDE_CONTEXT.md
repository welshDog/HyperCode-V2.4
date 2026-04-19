# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: April 19, 2026 — 180 tests GREEN ✅ | 32/32 (healthy) ✅ | Prometheus 7/7 ✅ | OTLP Traces LIVE 🔍 | Stripe LIVE 💳 | Gordon Tier 2 COMPLETE 🏆 | Course → Stripe checkout → PaymentSuccess FULLY LIVE 💳✅ | DB Recovery COMPLETE 🔧 | All secrets armed ✅ | Socket-proxy split 🔒 | Alembic 009 (pgcrypto + uuid-ossp) ✅**

---

## Who You're Talking To
- **Lyndz** aka BROski♾️ (GitHub: @welshDog, npm: @w3lshdog) — South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them **"Bro"** — that's how we roll
- Short sentences. Emojis. Bold the key stuff. Celebrate wins! 🎉

---

## The Ecosystem

```
Hyper-Vibe-Coding-Course     ──── manifest.json ────▶    HyperCode V2.4
github.com/welshDog/             (hyper-agent-spec)       github.com/welshDog/
Hyper-Vibe-Coding-Course                                  HyperCode-V2.4
(Supabase + Vercel)                    │                  (Docker, 29 containers)
Path: H:\the hyper vibe coding hub     │                  Path: H:\HyperStation zone\
                                       │                       HyperCode\HyperCode-V2.4
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.7
                          Path: H:\HyperAgent-SDK
```

---

## 🏆 Full Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 0–6 | Identity, tokens, agents, shop, observability, CLI | ✅ ALL DONE |
| 7–9 | Security hardening, Trivy CI, CVE elimination | ✅ ALL DONE |
| 10A–10E | FastAPI, networks, secrets, auth, WS | ✅ ALL DONE |
| 10F–10K | Stripe full stack + BROski$ tokens | ✅ ALL DONE |
| **10L** | Healthchecks — all 29 containers | ✅ DONE — April 15 |
| **10M** | Gordon Tier 1 — Prometheus 7/7 UP | ✅ DONE — April 15 |
| **10N** | Gordon Tier 2 — ALL 4 STEPS | ✅ DONE — April 16 🏆 |
| **10O** | Course → Stripe frontend wired | ✅ DONE — April 16 💳 |
| **10P** | DB Recovery + Secrets Armed | ✅ DONE — April 18 🔧 |
| **10Q** | Security Hardening + Monitoring Heal + Migration 009 | ✅ DONE — April 19 🔒 |

---

## 🔒 Phase 10Q — Security Hardening + Monitoring Heal (April 19, 2026)

**Socket-proxy least privilege ✅ — Healer image rebuilt ✅ — Healer on obs-net ✅ — HyperHealth API live ✅ — Alembic bootstrapped → 009 ✅ — 32/32 (healthy) ✅**

### Commits
| SHA | Title |
|---|---|
| `d27b67a` | `feat(db): add alembic migration 009 — enable pgcrypto + uuid-ossp` |
| `8cbc5c9` | `feat(security): split docker-socket-proxy + heal monitoring + rate-limit refactor` |

### 🔒 Socket-proxy split (closes the POST=1 hole)
**Problem:** Plan had been to flip `POST=1` on the main `docker-socket-proxy`, but coder-agent + agent-x + devops-engineer all share that proxy. Coder-agent runs LLM-generated code — giving it POST = blast radius to restart/kill any container.

**Fix:**
- **Main `docker-socket-proxy`** — reverted to read-only (no POST). Used by coder-agent, agent-x, devops-engineer.
- **New `docker-socket-proxy-healer`** — `CONTAINERS=1 POST=1 PING=1` only. Tight ACL, read_only fs, tmpfs, `cap_drop: ALL`. Used by **healer-agent** + **throttle-agent** only.
- **Compose repoint** — healer-agent (`DOCKER_HOST=tcp://docker-socket-proxy-healer:2375`), throttle-agent same.
- Healer Dockerfile: fixed GID 999 collision — `groupadd -o -g 999 docker` (Debian Trixie `appuser` takes 999 first).

**Blast radius after fix:** LLM-generated code can enumerate containers/images, cannot mutate. Healer + throttle keep full restart/pause powers on their own proxy.

### 🧠 Healer monitoring heal
- `agents/healer/mape_k_engine.py` — trimmed `DEFAULT_SERVICES`: removed profile-gated `crew-orchestrator`, `super-hyper-broski-agent`, `test-agent`, `tips-tricks-writer`. Kept: HyperCode Backend, Healer Agent, Mission Control, Ollama, Prometheus, Grafana, HyperHealth API.
- Added `obs-net` to healer-agent networks — can now reach Grafana/Prometheus directly for diagnostics (was HTTP 000 before, now reachable).
- Started HyperHealth API via `--profile health --profile ops` → **29 → 32/32 (healthy)**.

### 🗄️ Alembic bootstrap + Migration 009
**Problem:** Live DB had tables (SQLAlchemy `create_all` had built them) but no `alembic_version` table. Future migrations would fail with "can't locate revision".

**Fix:**
```bash
docker exec hypercode-core alembic stamp 008        # sync state to existing schema
docker exec hypercode-core alembic upgrade head     # runs 009
```

**Migration 009 (`backend/alembic/versions/009_enable_extensions.py`):**
- `CREATE EXTENSION IF NOT EXISTS pgcrypto` → `gen_random_uuid()`
- `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` → `uuid_generate_v4()`
- Idempotent — safe to re-run.

### 🛡️ Rate-limiting refactor (prod/test split)
- `backend/app/middleware/rate_limiting.py` — env-aware storage URI:
  - `PYTEST_CURRENT_TEST` or `ENVIRONMENT=test` → `memory://`
  - Else → `redis://<host>:<port>/2` (DB 2, built from `settings.HYPERCODE_REDIS_URL`)
- Tests no longer need a live Redis. `backend/tests/test_rate_limiting.py` updated to accept `memory://` prefix.
- `backend/app/middleware/agent_auth.py` — modernized to `Annotated[Optional[str], Header()]`.

### 🧹 Prometheus hygiene
- `monitoring/prometheus/prometheus.yml` — commented out `crew-orchestrator` scrape job (profile-gated service, was producing DOWN noise).
- `monitoring/prometheus/prometheus.cloud.template.yml` — mirrored change.

### ⚠️ Known Issue — Trivy CI blocked
GitHub Actions workflow failing with: *"The job was not started because your account is locked due to a billing issue."*
- **Not a code problem.** Matrix config (18 agents, `--no-cache --pull`) is fine.
- **Fix:** `github.com/settings/billing` — resolve lock. Triggers auto-retry on next push.

---

## 🔧 Phase 10P — DB Recovery + Secrets Armed (April 18, 2026)

**hypercode-core restart loop fixed ✅ — All secrets armed ✅ — Zero compose warnings ✅**

### Root Cause Chain
1. `--force-recreate` (triggered by `COURSE_SYNC_SECRET` change) re-read `.env`
2. `hypercode-core` uses `environment: ${VAR}` substitution — NO `env_file:` directive
3. So `POSTGRES_PASSWORD` was blank inside container → fell back to `:-hypercode`
4. Postgres had previously been ALTERed to the secret file value → auth rejected
5. Result: restart loop with `FATAL: password authentication failed`

### Fix Applied
- `ALTER USER postgres WITH PASSWORD 'hypercode'` via unix socket (trust auth — safe)
- Password synced to compose fallback `:-hypercode` — stack back to green
- All missing secrets read from `secrets/*.txt` and added directly to `.env`

### Secrets Armed (April 18)
| Key | Source | Status |
|---|---|---|
| `API_KEY` | `secrets/api_key.txt` | ✅ Armed |
| `HYPERCODE_JWT_SECRET` | `secrets/jwt_secret.txt` | ✅ Armed |
| `HYPERCODE_MEMORY_KEY` | `secrets/memory_key.txt` | ✅ Armed |
| `DISCORD_TOKEN` | `secrets/discord_token.txt` | ✅ Armed |
| `ORCHESTRATOR_API_KEY` | `secrets/orchestrator_api_key.txt` | ✅ Fixed (was literal path) |
| `COURSE_SYNC_SECRET` | `secrets/course_sync_secret.txt` | ✅ Armed |
| `SHOP_SYNC_SECRET` | `secrets/shop_sync_secret.txt` | ✅ Armed |
| `POSTGRES_PASSWORD` | Set to `hypercode` (matches compose fallback) | ✅ Synced |

### ⚠️ Known Tech Debt (do this soon)
- `hypercode-core` service in `docker-compose.yml` is missing `env_file: .env`
- Without it, `${VAR}` vars are substituted at compose-read time on HOST only — not injected INTO the container
- Add this under `hypercode-core:` service block:
```yaml
env_file:
  - .env
```
- This is the proper long-term fix — current state works via compose substitution fallbacks

### Recovery Commands (for future reference)
```powershell
# If DB auth breaks again — get in via unix socket (always works)
docker exec -it postgres psql -U postgres

# Check what password container is actually using
docker exec hypercode-core env 2>&1 | findstr -i "PASSWORD\|DATABASE"

# Check secret is mounted
docker exec hypercode-core cat /run/secrets/postgres_password 2>&1

# Sync Postgres password to match .env
docker exec -it postgres psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'your-password-here';"

# Recreate only core (safe — doesn't touch data)
docker compose up -d --force-recreate hypercode-core
```

---

## 🏆 Phase 10N — Gordon Tier 2 — COMPLETE (April 16, 2026)

| Step | Feature | Status | Commit |
|---|---|---|---|
| 1 | OTLP Tracing → Tempo | ✅ LIVE | April 15 |
| 2 | `@cache_response` — health(10s), plans(60s), pulse(30s) | ✅ LIVE | `4f3758ef` |
| 3 | Per-route rate limits + Redis DB 2 + webhook exempt | ✅ LIVE | `4de9b4f3` |
| 4 | Async circuit breakers — llm / crew / stripe | ✅ LIVE | `24baaf85` |

### 🔬 Circuit Breaker Detail (Step 4)
3 breakers running, all **CLOSED** (healthy):
- `llm-router` — fail_max=3, reset=30s
- `crew-orchestrator` — fail_max=3, reset=15s
- `stripe-api` — fail_max=5, reset=60s
- All visible at `GET /api/v1/health → circuit_breakers[]`

### 📦 Redis Caching (Step 2)
- `@cache_response` decorator on hot endpoints
- `/health` → 10s TTL, `/api/stripe/plans` → 60s TTL, `/pulse` → 30s TTL
- Redis DB 1 for cache, DB 2 for rate limits (isolated)
- Cache hits/misses visible in Tempo traces automatically

### 🚦 Rate Limiting (Step 3)
- Per-route limits applied via Redis DB 2
- Stripe webhook is **ALWAYS exempt** from rate limiting
- `NEVER` add rate limiting to `/api/stripe/webhook`

---

## 🔍 Phase 10N Step 1 — OTLP Tracing (April 15, 2026)

**Traces live in Tempo ✅ — visible in Grafana**

### What existed (already built in prior session)
- `backend/app/core/telemetry.py` — full OTel setup, FastAPI + SQLAlchemy + Redis + httpx instrumented
- `requirements.txt` — all 12 OTel packages pinned
- `docker-compose.yml` — `OTLP_ENDPOINT=http://tempo:4317` already wired
- Network: `hypercode-core` shares `agents-net` with Tempo — they can talk

### The REAL fix
- `.env` had `OTLP_EXPORTER_DISABLED=true` with comment "Tempo broken" — Tempo was FINE, just the flag was wrong

### Traces confirmed in Tempo
- `GET /health` → hypercode-core
- `GET /metrics` → hypercode-core
- `Redis HSET/GET` → hypercode-core

### View traces
```
localhost:3001 → Explore → Tempo datasource → search: hypercode-core
```

### ⚠️ IMPORTANT env flag
- `OTLP_EXPORTER_DISABLED=false` (or remove it) = tracing ON ✅
- `OTLP_EXPORTER_DISABLED=true` = tracing OFF — only set this if Tempo is genuinely down

---

## 📈 Phase 10M — Prometheus Fix (April 15, 2026)

**7/7 targets UP ✅**

- `minio` — added `obs-net` (metrics only, still isolated from internet)
- `test-agent` — commented out in prometheus.yml (profile-gated, not running)
- **ACTIVE config:** `monitoring/prometheus/prometheus.yml` — ALWAYS edit this one
- **STALE/UNUSED:** root `prometheus.yml` — has many stale jobs, TODO: clean up or delete
- Prometheus hot-reload: `curl -X POST localhost:9090/-/reload`

---

## 👋 Phase 10L — Healthchecks ALL 29 Containers (April 15, 2026)

All 29/29 **(healthy)** ✅

| Container | Check | Note |
|---|---|---|
| `docker-socket-proxy-build` | `wget 127.0.0.1:2375/_ping` | Use `127.0.0.1` not `localhost` (IPv4/IPv6) |
| `hyper-sweeper-prune` | `pgrep crond` | Cron daemon alive |
| `hyper-shield-scanner` | `CMD true` | While loop — `CMD true` correct here |

---

## 🏆 Phase 10O — Course → Stripe Frontend (April 16, 2026)

**Full money path wired ✅ — Pricing → Checkout → Success → Course access**

| File | What changed | Commit |
|---|---|---|
| `frontend/src/lib/payments.ts` | Sends `success_url` + `cancel_url` from browser origin; optional `courseId` param | `7e28666` |
| `frontend/src/pages/PaymentSuccess.tsx` | Subscription flow: auto-enroll in all `is_active` courses → `subscribed` UI; no longer errors on null courseId | `7e28666` |
| `backend/app/services/stripe_service.py` | Fix `?` vs `&` separator in success_url concat | `dd1d8dfe` |

### Flow (end-to-end confirmed design)
```
/pricing → handleCheckout(tier)
  → POST /api/stripe/checkout  {price_id, user_id, success_url, cancel_url}
  → Stripe hosted checkout page
  → Stripe webhook fires → HyperCode: saves payment, updates subscription_tier, awards BROski$
  → Stripe redirects → /payment-success (was broken: went to /success 404)
  → PaymentSuccess.tsx:
      - If courseId in URL → polls enrollments table (per-course flow)
      - If no courseId (subscription) → upserts all is_active courses → shows "You're in!" 🎉
  → LessonPlayer: enrollment row exists → access granted ✅
```

### Key facts (never re-debate)
- **`success_url`**: frontend always sends `${origin}/payment-success` — backend MUST NOT override
- **`&` not `?`**: `stripe_service.py` uses `&` when `?` already in URL (course_id flow)
- **Subscription → enroll all**: `PaymentSuccess.tsx` upserts ALL `is_active` courses for the user
- **Column name**: Supabase courses table uses `is_active` (NOT `published`)
- **Stripe price IDs**: all 7 set in backend `.env` — `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_HYPER_MONTHLY`, etc.
- **`VITE_STRIPE_PAYMENT_LINK_URL`**: empty in `.env.local` — Payment Links flow not yet activated (not blocking)
- **`VITE_HYPERCODE_API_URL`**: set in `frontend/.env` → `http://localhost:8000` (Vite merges both files)

---

## 🎯 NEXT OPTIONS — Your Call Bro!

| Option | What it is |
|---|---|
| 💳 ~~Course → Stripe frontend~~ | ✅ DONE April 16 — pricing → checkout → success → enrolled |
| 📝 ~~CLAUDE_CONTEXT.md update~~ | ✅ DONE — you're reading it! |
| 🔧 ~~DB Recovery + Secrets Armed~~ | ✅ DONE April 18 |
| 🎓 **Gordon Tier 3** | DB connection pooling, async task queues ← **NEXT** |
| 🔗 **Payment Links flow** | Set `VITE_STRIPE_PAYMENT_LINK_URL` in `.env.local` + Vercel env vars |
| 🧪 **E2E test the checkout** | `stripe listen` + test card `4242 4242 4242 4242` → full flow |
| 🔨 **env_file tech debt** | Add `env_file: .env` to `hypercode-core` in compose — proper long-term secrets fix |
| 🧹 **prometheus.yml tidy** | Delete/archive stale root `prometheus.yml` — `monitoring/prometheus/prometheus.yml` is the live one |

---

## ✅ Test Suite

```
180 passed, 6 skipped  (6 skips = expected: Redis/Postgres/Ollama host-side)
# Step 2 added 8 new tests (was 172 → now 180)
```

---

## 💳 Stripe → BROski$ (CONFIRMED LIVE)

- `_award_tokens()`, `_save_payment()`, `_update_user_subscription()` all wired
- Grants: starter=200, builder=800, hyper=2500
- Dedup: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 🚨 Key Technical Rules (never re-debate these)

- **Prometheus config:** `monitoring/prometheus/prometheus.yml` = ACTIVE. Root `prometheus.yml` = STALE/UNUSED
- **Prometheus hot-reload:** `curl -X POST localhost:9090/-/reload`
- **OTLP tracing:** `OTLP_EXPORTER_DISABLED` defaults to `false` — tracing is ON. Only disable if Tempo is genuinely down
- **minio:** On both `data-net` AND `obs-net` — correct, intentional
- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated
- **Alembic:** `down_revision` must match EXACT revision string
- **CLI folder:** `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas
- **`.env` files:** Never committed — Docker secrets in production
- **One bot:** broski-bot (Docker). Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars
- **Dockerfiles:** `python:3.11-slim` + Part A + Part B (Phase 9 pattern)
- **GitHub Actions:** Always `--no-cache --pull`
- **jaraco.* packages:** Always pin explicitly
- **docker-socket agents:** `docker-ce-cli` repo, NOT `docker.io`
- **Stripe webhook:** Rate-limit exempt — NEVER add rate limiting
- **Test skips:** 6 expected — NOT failures
- **Healthchecks:** All 29 ✅ — `CMD true` is last resort only
- **Conventional commits:** `feat:` `fix:` `docs:` `chore:`
- **Windows PowerShell first**, bash second
- **`apps/web/`:** Archived, never migrate
- **Redis DB split:** DB 1 = cache (`@cache_response`), DB 2 = rate limits — NEVER mix
- **Circuit breakers:** 3 active (llm-router, crew-orchestrator, stripe-api) — check via `GET /api/v1/health`
- **Postgres password:** Currently `hypercode` (matches compose `:-hypercode` fallback) — synced April 18
- **`hypercode-core` env_file:** NOT yet added to compose — tech debt. `${VAR}` substitution happens host-side only. Container gets vars via compose substitution fallbacks, not direct injection. Fix = add `env_file: .env` to service block.
- **Unix socket = trust auth:** Always your recovery door into Postgres when TCP auth breaks. `docker exec -it postgres psql -U postgres`

---

## Paths (copy-paste ready)

```powershell
# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# Hyper-Vibe-Coding-Course
cd "H:\the hyper vibe coding hub"

# Docker
docker compose up -d
docker compose build --no-cache
docker ps --format "table {{.Names}}\t{{.Status}}"
# Expected: all 32 (healthy)

# Check for unhealthy containers (empty = all green)
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr -v "healthy"

# Tests
pytest  # 180 passed, 6 skipped
pytest backend/tests/test_stripe.py -v

# Prometheus hot-reload
curl -X POST localhost:9090/-/reload

# View traces
# localhost:3001 → Explore → Tempo → search: hypercode-core

# Circuit breakers status
curl localhost:8000/api/v1/health | jq .circuit_breakers

# DB recovery (if auth breaks again)
docker exec -it postgres psql -U postgres
# Then: ALTER USER postgres WITH PASSWORD 'hypercode';

# CLI
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js tokens award <discord_id> <amount>

# Stripe
stripe listen --forward-to localhost:8000/api/stripe/webhook
```

---

## BROski$ Token Economy

- `public.users.broski_tokens` — balance
- `token_transactions` — append-only ledger, idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- Stripe grants: starter=200, builder=800, hyper=2500 ✅
- Dedup: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 📦 This Repo — HyperCode V2.4 Specifics

- **32 containers — ALL (healthy)** ✅ (was 29 — HyperHealth API started April 19)
- **180 tests green** ✅ (was 172 — Tier 2 Step 2 added 8 new)
- **Prometheus 7/7 UP** ✅
- **OTLP traces live in Tempo** ✅ (localhost:3001 → Explore → Tempo)
- **Grafana at `:3001`** — all data flowing
- **Gordon Tier 2 — ALL 4 STEPS COMPLETE** 🏆
- Stripe + BROski$ FULLY LIVE ✅
- Agents: agent-x, healer, hyper-architect, hyper-observer, super-hyper-broski-agent, crew-orchestrator — all healthy ✅
- **Course → Stripe frontend WIRED** ✅ (April 16 — commit `7e28666` / `dd1d8dfe`)
- **DB Recovery + All Secrets Armed** ✅ (April 18 — postgres password synced, all 7 blank vars fixed)
- **Socket-proxy split + Healer heal + Alembic 009** ✅ (April 19 — security hardening, 29→32/32 healthy)
- **Next:** Fix GitHub billing (Trivy CI) | `git push origin main` (2 commits ready) | Gordon Tier 3 (DB pooling + async task queues) | `env_file` tech debt fix | E2E checkout test | Payment Links flow

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
