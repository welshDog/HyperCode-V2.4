# 🤖 HyperAgent-SDK + Hyperfocus Zone — Claude Context Handoff
> Read this first. Every word. Then start the mission.
> **Last updated: April 14, 2026 — Phase 9 COMPLETE: CVE Elimination ✅**

---

## Who You're Talking To
- **Lyndz** aka BROski♾️ (GitHub: @welshDog, npm: @w3lshdog) — South Wales
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them **"Bro"** — that's how we roll
- Short sentences. Emojis. Bold the key stuff. Celebrate wins!

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

## 🏆 Roadmap — Phases 0–9 ALL COMPLETE!

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| 6 | Terminal Tools | ✅ DONE + VERIFIED LIVE |
| 7 | Dockerfile Security Hardening | ✅ DONE — April 14, 2026 |
| 8 | CI/CD Trivy Security Pipeline | ✅ DONE — April 14, 2026 |
| **9** | **CVE Elimination (apt + pip pinning)** | **✅ DONE — April 14, 2026** |

---

## 🎯 NEXT UP — Phase 10 Candidates

Choose one to start next:

| Option | Phase 10 | Why Now |
|--------|----------|----------|
| A | **FastAPI / Starlette upgrade** | Trivy flagged starlette HIGH — `fastapi>=0.117` fixes it. Quick win. |
| B | **Docker Compose network hardening** | Lock agents to internal networks, no accidental internet exposure |
| C | **Secrets management** (Docker secrets / Vault) | `.env` files still used locally — productionise secrets |
| D | **Agent-level rate limiting + auth** | Agents currently trust internal network — add per-agent API keys |

**Recommended: Option A first** (30 min job) then Option B.

---

## ✅ Phase 9 — CVE Elimination COMPLETE (April 14, 2026)

### Result — agent-x (Priority 1, was worst)

| Before | After |
|--------|-------|
| 11 CRITICAL, 55 HIGH | **0 CRITICAL, 14 HIGH** |

### The 14 Remaining HIGHs (Cannot be fixed at OS layer yet)
- `docker.io/runc` — moby Debian packaging lags behind official Docker releases
- `libexpat1` — new CVE, no Debian patch available yet
- `libncursesw6`, `libnghttp2`, `libsystemd0` — same, no Debian fix version yet
- `starlette` HIGH — **fixable**: upgrade FastAPI `0.116.1 → 0.117+` (Phase 10 Option A)

### What Was Patched Across All 19 Agents

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

**Part C — CI workflow fix (trivy-scan.yml):**
- Added `--no-cache --pull` to every build step
- Forces fresh base image pull → new OS patches picked up automatically in CI

**Bonus — docker-ce-cli swap:**
- `healer`, `coder`, `05-devops-engineer` switched from `docker.io` (Debian-packaged, stale)
  to `docker-ce-cli` from Docker's official apt repo
- Eliminates the `moby` HIGH CVEs in those 3 docker-socket agents

**Base image standardised:**
- All agents: `python:3.11.8-slim` → `python:3.11-slim`
- With `--pull` in CI, always gets latest 3.11 patch release automatically

---

## 🚨 Known Rules (never re-debate these)

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes BEFORE auth-gated compat routes
- **Alembic down_revision:** Must match EXACT revision string
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- **Port convention:** 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- **Supabase ↔ V2.4 Postgres:** NEVER merge schemas
- **`.env` files:** Never committed — use Docker secrets in production
- **One bot:** broski-bot. Old Replit bot = dead.
- **API keys:** `hc_` prefix + `secrets.token_urlsafe(32)`
- **Dockerfiles:** Use `python:3.11-slim` (not pinned patch) + Part A + Part B pattern — Phase 9
- **Trivy target:** 0 CRITICAL. <5 HIGH ideally. 14 HIGH remaining = no Debian fix available yet.
- **GitHub Actions builds:** Always `--no-cache --pull` in security scanning workflows
- **jaraco.* packages:** Always pin explicitly — Trivy HIGH via setuptools transitive
- **docker-socket agents** (healer/coder/05-devops): Use `docker-ce-cli` repo, NOT `docker.io`
- **starlette HIGH:** Fix = `fastapi>=0.117` — scheduled for Phase 10

---

## ✅ Phases 0–8 — Full History (condensed)

### HyperAgent-SDK ✅ SHIPPED
- CLI: validate, status, logs, tokens, agents, graduate — all verified
- Published: `@w3lshdog/hyper-agent@0.1.4` live on npm ✅

### Phase 0 ✅ — Port conflicts, xp-leaderboard, Alembic migration
### Phase 1 ✅ — discord_id bridge, /coursestats Discord command, Edge Function
### Phase 2 ✅ — Token sync, CourseSyncEvent, /award-from-course, dedup guards
### Phase 3 ✅ — AccessProvision, /provision, shop trigger, Discord DM delivery
### Phase 4 ✅ — GraduationEvent ORM, /graduate/trigger, Edge Function
### Phase 5 ✅ — Structured JSON logging, MetricsMiddleware, /health + /metrics live, Grafana
### Phase 6 ✅ — 5 CLI commands verified. Logs routing fix (broadcaster before dashboard_compat)

### Phase 7 ✅ (April 14, 2026)
19 Dockerfiles patched: non-root users, docker group (GID 999), multi-stage rewrite for tips-tricks-writer, env+healthcheck gaps

### Phase 8 ✅ (April 14, 2026)
- `trivy-scan.yml` — PR gate, pinned `@0.28.0`, smart root/local build context split, SARIF upload
- `trivy-weekly.yml` — Monday 06:00 UTC, Python aggregator, 90-day artifact retention
- `trivy-pre-push.sh` — local hook, auto-detects Trivy binary or Docker fallback
- `Makefile` — `scan-agent`, `scan-all`, `scan-build`, `trivy-hook-install`

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
docker compose exec api alembic upgrade head

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
```

---

## npm / SDK Quick Reference

```powershell
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
- Stripe integration for token packs (Starter/Builder/Hyper)
