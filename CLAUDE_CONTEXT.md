# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: April 15, 2026 (10pm) — 172 tests GREEN ✅ | 29/29 (healthy) ✅ | Prometheus 7/7 ✅ | OTLP Traces LIVE 🔍 | Stripe LIVE 💳**

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
| **10N** | Gordon Tier 2 Step 1 — OTLP Tracing | ✅ DONE — April 15 🔍 |

---

## 🔍 Phase 10N — Gordon Tier 2 Step 1: OTLP Tracing (April 15, 2026)

**Traces live in Tempo ✅ — visible in Grafana**

### What existed (already built in prior session)
- `backend/app/core/telemetry.py` — full OTel setup, FastAPI + SQLAlchemy + Redis + httpx instrumented
- `requirements.txt` — all 12 OTel packages pinned
- `docker-compose.yml` — `OTLP_ENDPOINT=http://tempo:4317` already wired
- Network: `hypercode-core` shares `agents-net` with Tempo — they can talk

### What was actually broken (the REAL fix)
- `.env` had `OTLP_EXPORTER_DISABLED=true` with comment "Tempo broken" — Tempo was FINE, just the flag was wrong

### Two commits applied
1. `config.py` default `True` → `False` — tracing ON unless explicitly overridden
2. Prometheus `--web.enable-lifecycle` — hot-reload config with `curl -X POST :9090/-/reload`

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

## 🎯 NEXT UP — Gordon Tier 2 Remaining

| Step | Task | Status |
|---|---|---|
| 1 | OTLP Tracing → Tempo | ✅ DONE |
| **2** | **Redis caching decorator on hot endpoints** | ⏳ NEXT |
| 3 | Circuit breaker — agent failure isolation | ⏳ Queued |
| 4 | Rate limiting polish | ⏳ Queued |
| 5 | Task C — Vibe Course frontend → Stripe | ⏳ Queued |

### Step 2 — Redis Caching Notes
- `@cache_response` decorator pattern — wire onto hot endpoints
- Redis is on `data-net` — already accessible from `hypercode-core`
- With tracing live, cache hits/misses will show in Tempo automatically
- Target endpoints: `/api/stripe/plans`, `/health`, any leaderboard/token balance reads

---

## ✅ Test Suite

```
172 passed, 6 skipped  (6 skips = expected: Redis/Postgres/Ollama host-side)
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
# Expected: all 29 (healthy)

# Tests
pytest  # 172 passed, 6 skipped
pytest backend/tests/test_stripe.py -v

# Prometheus hot-reload
curl -X POST localhost:9090/-/reload

# View traces
# localhost:3001 → Explore → Tempo → search: hypercode-core

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

- **29 containers — ALL (healthy)** ✅
- **172 tests green** ✅
- **Prometheus 7/7 UP** ✅
- **OTLP traces live in Tempo** ✅ (localhost:3001 → Explore → Tempo)
- **Grafana at `:3001`** — all data flowing
- Stripe + BROski$ FULLY LIVE ✅
- Agents: agent-x, healer, hyper-architect, hyper-observer, super-hyper-broski-agent, crew-orchestrator — all healthy ✅
- **Next:** Gordon Tier 2 Step 2 — Redis caching `@cache_response` decorator

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
