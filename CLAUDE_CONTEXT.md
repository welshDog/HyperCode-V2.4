# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: April 15, 2026 (9:42pm) — 172 tests GREEN ✅ | 29/29 ALL (healthy) ✅ | Prometheus 7/7 UP ✅ | Stripe→BROski$ LIVE 💳**

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
| 7 | Dockerfile Security Hardening | ✅ DONE — April 14 |
| 8 | CI/CD Trivy Security Pipeline | ✅ DONE — April 14 |
| 9 | CVE Elimination | ✅ DONE — April 14 |
| 10A | FastAPI / Starlette upgrade | ✅ DONE |
| 10B | Docker Compose Network Isolation | ✅ DONE — April 14 |
| 10C | Docker Secrets | ✅ DONE — April 14 |
| 10D | Agent-level rate limiting + auth | ✅ DONE — April 14 🔑 |
| 10E | CognitiveUplink WS type fix | ✅ DONE — April 15 |
| 10F | Stripe Checkout API | ✅ DONE — April 14 💳 |
| 10G | DB — Stripe webhook writes + BROski$ tokens | ✅ DONE — April 14 |
| 10H | Pricing page (dashboard) | ✅ DONE — April 14 |
| 10I | Stripe CLI e2e LIVE | ✅ DONE — April 15 🎉 |
| 10J | CognitiveUplink `/ws/uplink` | ✅ DONE — April 15 🔌 |
| 10K | Stripe Price IDs in `.env` | ✅ DONE — April 15 |
| **10L** | **Healthchecks — all 29 containers** | ✅ DONE — April 15 👋 |
| **10M** | **Gordon Tier 1 — Prometheus 7/7 UP** | ✅ DONE — April 15 📈 |

---

## 📈 Phase 10M — Gordon Tier 1 Prometheus Fix (April 15, 2026)

**Result: 7/7 Prometheus targets UP ✅**

| Target | Root cause | Fix |
|---|---|---|
| `hypercode-core` | Already fixed in prior session | No change needed |
| `minio` DOWN | Phase 10B network isolation — `data-net` ↔ `obs-net` couldn't talk | Added `obs-net` to minio in `docker-compose.yml` — metrics only, still isolated from internet |
| `test-agent` DOWN | Container profile-gated, not running | Commented out in `prometheus.yml` (same pattern as `throttle-agent`) |

### ⚠️ IMPORTANT — Prometheus Config Files
- **ACTIVE config:** `monitoring/prometheus/prometheus.yml` — THIS is the one Prometheus reads
- **STALE/UNUSED:** root `prometheus.yml` — has many stale jobs pointing at agents that aren’t running
- **TODO (future):** Clean up root `prometheus.yml` or delete it to avoid confusion
- **Rule:** Always edit `monitoring/prometheus/prometheus.yml` — never the root one

---

## 👋 Phase 10L — Healthchecks ALL 29 Containers (April 15, 2026)

All 29/29 containers show **(healthy)** ✅

| Container | Check | Why |
|---|---|---|
| `docker-socket-proxy-build` | `wget 127.0.0.1:2375/_ping` | HAProxy `/_ping` — use `127.0.0.1` not `localhost` (IPv4/IPv6) |
| `hyper-sweeper-prune` | `pgrep crond` | Verifies cron daemon alive |
| `hyper-shield-scanner` | `CMD true` | Long-running while loop — no HTTP, `CMD true` is correct here |

**Rule:** Meaningful check first. `CMD true` = last resort only.

---

## ✅ Test Suite

```
172 passed, 6 skipped  (6 skips = expected: Redis/Postgres/Ollama)
```

---

## 💳 Stripe → BROski$ (Phase 10G — CONFIRMED)

- `_award_tokens()`, `_save_payment()`, `_update_user_subscription()` all wired
- Token grants: starter=200, builder=800, hyper=2500
- Dedup: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 🎯 NEXT UP

| # | Task | Size |
|---|---|---|
| **Gordon Tier 2** | OTLP tracing, Redis caching, rate limiting, or circuit breaker | Medium |
| **Task C** | Wire Vibe Course frontend → Stripe checkout | Bigger |
| **Cleanup** | Delete / fix root `prometheus.yml` (stale jobs) | Small |

**Gordon Tier 2 options — ask Lyndz which one:**
- 🔍 OTLP tracing — distributed traces in Grafana/Tempo
- ⚡ Redis caching — cache hot API responses
- 🚦 Rate limiting improvements
- 🔌 Circuit breaker — stop cascading failures between agents

---

## 🌐 Docker Network Topology (Phase 10B — LIVE)

- `frontend-net` (bridge, internet) — dashboard, mission-ui, mcp-server
- `backend-net` (bridge, internet) — hypercode-core
- `agents-net` (bridge, internet) — all AI agents
- `data-net` (bridge, **internal: true**) — redis + postgres + minio + chroma
- `obs-net` (bridge, **internal: true**) — prometheus, grafana, loki, tempo, promtail

**Note:** minio now also on `obs-net` (metrics only) — still isolated from internet ✅

---

## 🛡️ Phase 9 Security Patterns (ALL new Dockerfiles)

**Part A — OS hardening:**
```dockerfile
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```
**Part B — pip pinning:**
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"
```
**Base image:** `python:3.11-slim` | **Trivy:** 0 CRITICAL target, 14 HIGH = no Debian fix yet

---

## 🚨 Key Technical Rules (never re-debate these)

- **Prometheus config:** ALWAYS edit `monitoring/prometheus/prometheus.yml` — root `prometheus.yml` is STALE/UNUSED
- **minio:** Now on both `data-net` AND `obs-net` — correct, intentional
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
- **Dockerfiles:** `python:3.11-slim` + Part A + Part B
- **GitHub Actions:** Always `--no-cache --pull`
- **jaraco.* packages:** Always pin explicitly
- **docker-socket agents:** `docker-ce-cli` repo, NOT `docker.io`
- **Stripe webhook:** Rate-limit exempt — NEVER add rate limiting
- **Stripe dev mode:** Missing `STRIPE_WEBHOOK_SECRET` = sig check skipped (local only)
- **Test skips:** 6 expected — NOT failures
- **Healthchecks:** All 29 ✅ — `CMD true` is last resort
- **Conventional commits:** `feat:` `fix:` `docs:` `chore:`
- **Windows PowerShell first**, bash second
- **`apps/web/`:** Archived, never migrate

---

## Paths (copy-paste ready)

```powershell
# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4\backend"

# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# Hyper-Vibe-Coding-Course
cd "H:\the hyper vibe coding hub"

# Docker
docker compose up -d
docker compose build --no-cache
docker compose exec api alembic upgrade head
docker ps --format "table {{.Names}}\t{{.Status}}"
# Expected: all 29 (healthy)

# Tests
pytest  # Expected: 172 passed, 6 skipped
pytest backend/tests/test_stripe.py -v

# Security
make scan-all
make scan-agent AGENT=healer

# CLI
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js tokens award <discord_id> <amount>

# Stripe
stripe listen --forward-to localhost:8000/api/stripe/webhook
curl -X POST http://localhost:8000/api/stripe/checkout \
  -H "Content-Type: application/json" \
  -d '{"price_id": "starter", "user_id": "broski_test"}'
```

---

## BROski$ Token Economy

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger, idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- Stripe grants: starter=200, builder=800, hyper=2500 BROski$ ✅
- Dedup: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 📦 This Repo — HyperCode V2.4 Specifics

- **29 containers — ALL (healthy)** ✅
- **172 tests green** ✅
- **Prometheus 7/7 targets UP** ✅
- **Grafana at `:3000`** — all data flowing
- Stripe + BROski$ tokens FULLY LIVE ✅
- Agents: agent-x, healer, hyper-architect, hyper-observer, super-hyper-broski-agent, crew-orchestrator — all healthy ✅
- **Next:** Gordon Tier 2 OR Task C (Vibe Course Stripe wiring)

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
