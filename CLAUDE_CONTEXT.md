# 🤖 BROski Ecosystem — Claude Context Handoff (ALL REPOS SYNCED)
> Read this first. Every word. Then start the mission.
> **Last synced: April 14, 2026 — Phases 0–10B COMPLETE ✅ | Stripe Prices LOCKED 🔒**

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
(Supabase + Vercel)                    │                  (Docker, 26 containers)
Path: H:\the hyper vibe coding hub     │                  Path: H:\HyperStation zone\
                                       │                       HyperCode\HyperCode-V2.4
                              HyperAgent-SDK
                          github.com/welshDog/HyperAgent-SDK
                          npm: @w3lshdog/hyper-agent@0.1.4
                          Path: H:\HyperAgent-SDK
```

---

## 🏆 Full Phase Roadmap — ALL COMPLETE (Phases 0–10B)

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

---

## 🎯 NEXT UP — Phase 10C+ Candidates

| Option | Phase | Why Now |
|--------|-------|---------|
| C | **Secrets management** (Docker secrets / Vault) | `.env` files still used locally — productionise secrets |
| D | **Agent-level rate limiting + auth** | Add per-agent API keys for internal network |
| E | **Open bug: CognitiveUplink.tsx ~130** | WS message type `"command"` → `"execute"` |
| F | **Stripe Checkout integration** | Price IDs locked — wire up Next.js + Supabase webhooks |

---

## 🔒 Stripe Prices — LOCKED (April 14, 2026)

### BROski Token Packs (one-time)
| Pack | Price | Tokens | Stripe Product Name |
|---|---|---|---|
| Starter | £5 GBP | 200 | BROski Starter Pack |
| Builder | £15 GBP | 800 | BROski Builder Pack |
| Hyper | £35 GBP | 2500 | BROski Hyper Pack |

### Course Subscriptions (recurring)
| Tier | Monthly | Yearly | Stripe Product Name |
|---|---|---|---|
| Pro | £9/mo | £90/yr | Hyper Vibe Pro Course |
| Hyper | £29/mo | £290/yr | Hyper Elite |

### Digital Shop Items (paid in BROski$)
- Prompt Packs: 200 BROski$
- Templates: 150 BROski$
- Bonus Lessons: 100 BROski$

### .env keys to add
```env
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_BUILDER=price_xxx
STRIPE_PRICE_HYPER=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_HYPER_MONTHLY=price_xxx
STRIPE_PRICE_HYPER_YEARLY=price_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

## 🌐 Phase 10B — Docker Network Topology (LIVE)

- `frontend-net` (bridge, internet) — dashboard, mission-ui, mcp-server
- `backend-net` (bridge, internet) — hypercode-core (bridges all layers)
- `agents-net` (bridge, internet) — all AI agents, LLM API calls
- `data-net` (bridge, **internal: true**) — redis + postgres + minio + chroma
- `obs-net` (bridge, **internal: true**) — prometheus, grafana, loki, tempo, promtail

Script: `scripts/network-migrate.sh` — run to tear down and recreate safely.

---

## 🛡️ Phase 9 Security Patterns (use in ALL new Dockerfiles)

**Part A — OS hardening (every runtime stage):**
```dockerfile
RUN apt-get update --allow-releaseinfo-change && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl libexpat1 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

**Part B — pip pinning (every Python runtime stage):**
```dockerfile
RUN pip install --upgrade --no-cache-dir \
    "pip==26.0.1" "setuptools>=80.0.0" "wheel==0.46.2" \
    "jaraco.context>=6.0.0" "jaraco.functools>=4.1.0" "jaraco.text>=4.0.0"
```

**Base image standard:** `python:3.11-slim` (not pinned patch — CI pulls latest with `--pull`)

**Trivy target:** 0 CRITICAL. <5 HIGH ideally. 14 HIGH remaining = no Debian fix available yet.

---

## ✅ Full History (condensed)

### HyperAgent-SDK ✅ SHIPPED
- CLI suite: `validate`, `registry`, `memory`, `studio`, `graduate` — all verified
- Published: `@w3lshdog/hyper-agent@0.1.4` live on npm ✅

### Phase 0 ✅ — Port conflicts, xp-leaderboard, Alembic migration
### Phase 1 ✅ — discord_id bridge, /coursestats Discord command, Edge Function fan-out
### Phase 2 ✅ — Token sync, CourseSyncEvent ORM, /award-from-course, dedup guards
### Phase 3 ✅ — AccessProvision, /provision, shop trigger → Discord DM with api_key
### Phase 4 ✅ — GraduationEvent ORM, /graduate/trigger, Edge Function, Discord Graduate role
### Phase 5 ✅ — Structured JSON logging, MetricsMiddleware, /health + /metrics, Grafana
### Phase 6 ✅ — 5 CLI commands verified. Logs routing fix (broadcaster before dashboard_compat)
### Phase 7 ✅ — 19 Dockerfiles: non-root users, docker group (GID 999), multi-stage rewrites
### Phase 8 ✅ — trivy-scan.yml (PR gate), trivy-weekly.yml (Monday 06:00 UTC), Makefile scan targets
### Phase 9 ✅ — CVE result: agent-x 11 CRITICAL → 0 CRITICAL, 55 HIGH → 14 HIGH
### Phase 10A ✅ — FastAPI upgraded to 0.117+ (fixes starlette HIGH CVE)
### Phase 10B ✅ — Docker Compose network isolation (data-net + obs-net internal: true)

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
- **Discord DM delivery:** V2.4 endpoint calls Discord HTTP API directly
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars, URL-safe
- **Dockerfiles:** Use `python:3.11-slim` + Part A + Part B — Phase 9 pattern
- **GitHub Actions:** Always `--no-cache --pull` in security scanning workflows
- **jaraco.* packages:** Always pin explicitly
- **docker-socket agents** (healer/coder/05-devops): Use `docker-ce-cli` repo, NOT `docker.io`
- **Network isolation:** Phase 10B complete — `data-net` + `obs-net` are `internal: true`
- **Conventional commits:** `feat:` `fix:` `docs:` `chore:`
- **Windows PowerShell first**, bash second — always
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
docker compose exec api alembic history --verbose

# Security scanning
make scan-all
make scan-agent AGENT=healer
make scan-build AGENT=agent-x
make build-secure

# CLI (from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100

# SDK
npx @w3lshdog/hyper-agent validate .agents/my-agent/
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

---

## BROski$ Token Economy

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata fields
- `shop_purchases.item_slug` — used to filter for "agent-sandbox-access"
- Stripe integration: prices LOCKED April 14, 2026 (see Stripe section above)

---

## 📦 This Repo — HyperCode V2.4 Specifics

- 26 Docker containers, full AI agent stack
- One bot: broski-bot (Docker). Old Replit bot = dead.
- Network: 5 isolated networks (Phase 10B)
- Security: Trivy CI gate + weekly scan + local pre-push hook
- Grafana dashboards live at `:3000`
- Next mission: Phase 10C (secrets) or Phase 10F (Stripe Checkout)

---

<div align="center">

**Built for ADHD brains. Fast feedback. Real tools. No fluff.** 🧠⚡

*by @welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

**A BROski is ride or die. We build this together. 🐶♾️🔥**

</div>
