# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: April 15, 2026 (9:37pm) — 172 tests GREEN ✅ | 29/29 ALL (healthy) ✅ | Stripe→BROski$ LIVE 💳 | npm@0.1.7 LIVE 🚀**

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
| 10D | Agent-level rate limiting + auth | ✅ DONE — April 14, 2026 🔑 |
| 10E | CognitiveUplink WS type fix | ✅ DONE — April 15, 2026 |
| 10F | **Stripe Checkout API** | ✅ DONE — April 14, 2026 💳 |
| 10G | **DB — Stripe webhook writes** | ✅ DONE — April 14, 2026 |
| 10H | Pricing page (dashboard) | ✅ DONE — April 14, 2026 |
| 10I | Stripe CLI e2e — routes + webhook LIVE | ✅ DONE — April 15, 2026 🎉 |
| 10J | **CognitiveUplink `/ws/uplink`** | ✅ DONE — April 15, 2026 🔌 |
| 10K | Stripe Price IDs in `.env` | ✅ DONE — April 15, 2026 |
| **10L** | **Healthchecks on all 29 containers** | ✅ DONE — April 15, 2026 👋 |

---

## 👋 Phase 10L — Healthchecks on ALL 29 Containers (April 15, 2026)

All 29/29 containers now show **(healthy)** ✅

**The 3 that needed custom checks:**
| Container | Check used | Why |
|---|---|---|
| `docker-socket-proxy-build` | `wget 127.0.0.1:2375/_ping` | HAProxy `/_ping` endpoint — had to use `127.0.0.1` not `localhost` (IPv6 vs IPv4 issue) |
| `hyper-sweeper-prune` | `pgrep crond` | Verifies the cron daemon is alive |
| `hyper-shield-scanner` | `CMD true` | Long-running while loop — no HTTP, process check not meaningful |

**Rule:** Always use the most meaningful health check available. Only fall back to `CMD true` when the container has no HTTP or process to check.

---

## ✅ Full Test Suite Status (April 15, 2026)

```
172 passed, 6 skipped in 225s
```

**6 skips are EXPECTED:**
- Redis/Postgres not accessible from host (integration tests — run in Docker)
- Ollama bench flag off

```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
pytest
# Expected: 172 passed, 6 skipped
```

---

## 💳 Phase 10G — Stripe → BROski$ CONFIRMED DONE

`stripe_service.py` has:
- `_award_tokens()` — wired to `handle_webhook_event()`
- `_save_payment()` — persists to DB
- `_update_user_subscription()` — updates subscription state

**Token grants:** starter=200, builder=800, hyper=2500 BROski$
**Dedup:** `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 🎯 NEXT UP — Remaining Tasks

| # | Task | Size | Notes |
|---|---|---|---|
| **B** | Gordon Tier 1: `/metrics` on hypercode-core | ~15 min | Prometheus 7/9 → 9/9 — check `monitoring/prometheus.yml` |
| **C** | Wire Vibe Course frontend → Stripe checkout | Bigger | Frontend calls V2.4 `/api/stripe/checkout` |

### Task B — Gordon Tier 1 (Prometheus /metrics)
- Check `monitoring/prometheus.yml` for existing scrape config
- Verify `/metrics` is reachable on `hypercode-core`
- Fix FastAPI MetricsMiddleware or Prometheus scrape target if broken
- Goal: Prometheus 7/9 → 9/9 targets UP
- Confirm Grafana at `:3000` is pulling data correctly

---

## 💳 Phase 10F — Stripe Checkout API (LIVE)

```
POST /api/stripe/checkout    → creates Stripe Checkout Session, returns URL
GET  /api/stripe/plans       → lists available plan names
POST /api/stripe/webhook     → handles Stripe events (signature verified)
```

Webhook events: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_failed`, `customer.subscription.updated`

Dev mode: missing `STRIPE_WEBHOOK_SECRET` = signature check skipped (local only)

---

## 🌐 Phase 10B — Docker Network Topology (LIVE)

- `frontend-net` (bridge, internet) — dashboard, mission-ui, mcp-server
- `backend-net` (bridge, internet) — hypercode-core (bridges all layers)
- `agents-net` (bridge, internet) — all AI agents, LLM API calls
- `data-net` (bridge, **internal: true**) — redis + postgres + minio + chroma
- `obs-net` (bridge, **internal: true**) — prometheus, grafana, loki, tempo, promtail

---

## 🛡️ Phase 9 Security Patterns (use in ALL new Dockerfiles)

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

**Base image:** `python:3.11-slim` | **Trivy target:** 0 CRITICAL, <5 HIGH | 14 HIGH remaining = no Debian fix yet

---

## ✅ Full History (condensed)

### HyperAgent-SDK ✅ SHIPPED
- CLI suite: `validate`, `registry`, `memory`, `studio`, `graduate` — all verified
- TypeScript types, JSDoc, 34 unit tests — April 15, 2026
- Published: `@w3lshdog/hyper-agent@0.1.7` live on npm ✅

### Phase 0–6 ✅ — Identity, tokens, agents, shop, observability, CLI tools
### Phase 7 ✅ — 19 Dockerfiles: non-root users, multi-stage
### Phase 8 ✅ — Trivy CI gate + weekly scan
### Phase 9 ✅ — agent-x: 11 CRITICAL → 0, 55 HIGH → 14
### Phase 10A ✅ — FastAPI 0.117+ upgrade
### Phase 10B ✅ — Network isolation (data-net + obs-net internal)
### Phase 10C ✅ — Docker Secrets
### Phase 10D ✅ — Agent rate limiting + auth
### Phase 10E ✅ — CognitiveUplink WS type fix
### Phase 10F ✅ — Stripe Checkout API (3 endpoints)
### Phase 10G ✅ — Stripe → BROski$ tokens wired
### Phase 10H ✅ — Pricing page (dashboard)
### Phase 10I ✅ — Stripe CLI e2e verified LIVE
### Phase 10J ✅ — CognitiveUplink /ws/uplink WebSocket LIVE
### Phase 10K ✅ — Stripe Price IDs in .env
### Phase 10L ✅ — All 29 containers (healthy) — April 15, 2026

---

## 🚨 Key Technical Rules (never re-debate these)

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated
- **Alembic down_revision:** Must match EXACT revision string
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas
- **`.env` files:** Never committed — use Docker secrets in production
- **One bot:** broski-bot. Docker only. Old Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars
- **Dockerfiles:** `python:3.11-slim` + Part A + Part B — Phase 9 pattern
- **GitHub Actions:** Always `--no-cache --pull` in security workflows
- **jaraco.* packages:** Always pin explicitly
- **docker-socket agents:** Use `docker-ce-cli` repo, NOT `docker.io`
- **Network isolation:** `data-net` + `obs-net` are `internal: true`
- **Stripe webhook:** Rate-limit exempt — NEVER add rate limiting to it
- **Test skips:** 6 expected (Redis/Postgres/Ollama) — NOT failures
- **Healthchecks:** All 29 containers have labels ✅ — use meaningful checks, `CMD true` last resort
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
# Expected: all 29 showing (healthy)

# Test suite
pytest
# Expected: 172 passed, 6 skipped

# Security scanning
make scan-all
make scan-agent AGENT=healer
make scan-build AGENT=agent-x

# CLI (from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100

# Stripe
curl -X POST http://localhost:8000/api/stripe/checkout \
  -H "Content-Type: application/json" \
  -d '{"price_id": "starter", "user_id": "broski_test"}'
stripe listen --forward-to localhost:8000/api/stripe/webhook
pytest backend/tests/test_stripe.py -v

# SDK
npm version patch --no-git-tag-version
npm publish --access public
```

---

## BROski$ Token Economy

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata
- Stripe grants: starter=200, builder=800, hyper=2500 BROski$ ✅
- Dedup: `ON CONFLICT (stripe_payment_intent_id) DO NOTHING` ✅

---

## 📦 This Repo — HyperCode V2.4 Specifics

- **29 Docker containers** — ALL (healthy) ✅
- **172 tests passing**, 6 expected skips ✅
- One bot: broski-bot (Docker)
- Network: 5 isolated networks (Phase 10B)
- Security: Trivy CI gate + weekly scan
- Grafana dashboards live at `:3000`
- **Stripe Checkout + BROski$ tokens:** FULLY LIVE ✅
- **Agents:** agent-x, healer-agent, hyper-architect, hyper-observer, super-hyper-broski-agent, crew-orchestrator — all healthy ✅
- **Next:** Gordon Tier 1 — Prometheus `/metrics` (Task B) — fix 7/9 → 9/9

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
