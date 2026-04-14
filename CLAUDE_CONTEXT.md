# 🤖 HyperAgent-SDK + Hyperfocus Zone — Claude Context Handoff
> Read this first. Every word. Then start the mission.
> **Last updated: April 14, 2026 — Phase 7: Agents Security Upgrade**

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

## Roadmap — Phases 0–6 COMPLETE 🏆 + Phase 7 IN PROGRESS

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| 6 | Terminal Tools | ✅ DONE + VERIFIED LIVE |
| **7** | **Agents Security Upgrade** | **🟡 IN PROGRESS — April 14, 2026** |

---

## 🚨 PHASE 7 — Agents Security Upgrade (CURRENT)

### Mission
Trivy scan (April 14, 2026) found HIGH + CRITICAL CVEs in all 12 agent images.
Root cause: stale Debian 12.5 base images + unupgraded OS packages.

### 12 Agent Images to Patch
```
hypercode-v24-agent-x           ← 🔴 PRIORITY 1 (11 CRITICAL, 55 HIGH)
hypercode-v24-celery-worker     ← 🔴 PRIORITY 2
hypercode-v24-crew-orchestrator ← 🔴 PRIORITY 3
hypercode-v24-healer-agent      ← 🔴 PRIORITY 4
hypercode-v24-broski-bot        ← 🟡 (0 CRITICAL, 51 HIGH)
hypercode-v24-hyper-architect
hypercode-v24-hyper-observer
hypercode-v24-hyper-worker
hypercode-v24-hypercode-mcp-server
hypercode-v24-test-agent
hypercode-v24-throttle-agent
hypercode-v24-tips-tricks-writer
```

### The Fix — Apply to EVERY Dockerfile
```dockerfile
# 1. Use latest patched slim base
FROM python:3.11-slim

# 2. Upgrade ALL OS packages (kills libexpat1, glibc, openssl CVEs)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Upgrade pip tools (kills jaraco.context, wheel CVEs)
RUN pip install --upgrade --no-cache-dir \
    pip==26.0.1 \
    setuptools>=80.0.0 \
    wheel==0.46.2

# 4. Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

### Verify Each Fix
```powershell
docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet hypercode-v24-agent-x
```
Target: **ZERO CRITICAL, <5 HIGH** per image.

### Phase 7 Deliverable
Create `SECURITY_PATCH_REPORT.md` summarising every Dockerfile changed, CVEs before/after, and verification scan results.

---

## ✅ Phases 0–6 — Full History

### HyperAgent-SDK ✅ SHIPPED
- `cli/validate.js` — AJV validator, coloured output, exit codes
- `hyper-agent-spec.json` — JSON Schema, if/then port enforcement
- `templates/python-starter/` + `templates/node-starter/` — both valid
- `npm test` — 2/2 passing ✅
- Published: `@w3lshdog/hyper-agent@0.1.4` live on npm ✅

### Phase 0 ✅ DONE
- `docker-compose.yml` — port 5432 removed, apps/web dropped
- `discord-bot/cogs/xp.py` — /leaderboard → /xp-leaderboard
- `002_add_discord_id_to_users.py` — Alembic migration created

### Phase 1 ✅ DONE + VERIFIED
1. `backend/alembic/versions/003_add_discord_id.py`
2. `backend/app/models/models.py` — discord_id on User ORM
3. `backend/app/schemas/schemas.py` — discord_id in UserBase
4. `backend/app/api/v1/endpoints/users.py` — GET /api/v1/users/by-discord/{discord_id}
5. `supabase/functions/course-profile/index.ts`
6. `agents/broski-bot/src/cogs/course_stats.py` — /coursestats Discord command
7. `bot.py` + `settings.py` — wired cog + course_profile_edge_url
**Verified:** /coursestats shows dual-system embed ✅

### Phase 2 ✅ DONE + VERIFIED
1. `backend/alembic/versions/004_add_course_sync_events.py`
2. `backend/app/models/broski.py` — CourseSyncEvent ORM model
3. `backend/app/core/config.py` — COURSE_SYNC_SECRET
4. `backend/app/api/v1/endpoints/economy.py` — POST /api/v1/economy/award-from-course
5. `backend/app/api/api.py` — economy router wired
6. `supabase/functions/sync-tokens-to-v24/index.ts`
**Dedup:** App-level 409 check + DB UNIQUE constraint on source_id ✅

### Phase 3 ✅ DONE + VERIFIED
1. `backend/alembic/versions/005_add_access_provisions.py`
2. `backend/app/models/models.py` — AccessProvision ORM model added
3. `backend/app/api/v1/endpoints/access.py` — POST /api/v1/access/provision
4. `backend/app/core/config.py` — SHOP_SYNC_SECRET, DISCORD_BOT_TOKEN, MISSION_CONTROL_URL
5. `supabase/functions/provision-access/index.ts` — fires on shop_purchases INSERT
6. Router wired in `backend/app/api/api.py`
**Verified:** Buy "Agent Sandbox Access" → Discord DM with api_key + mission_control_url ✅

### Phase 4 ✅ DONE + VERIFIED
1. `backend/alembic/versions/006_add_graduation_events.py`
2. `backend/app/models/graduate.py` — GraduationEvent ORM model
3. `backend/app/api/v1/endpoints/graduate.py` — POST /api/v1/graduate/trigger
4. `supabase/functions/graduate-student/index.ts`
5. Router wired in `backend/app/api/api.py`
**Table confirmed:** public.graduation_events ✅

### Phase 5 ✅ DONE + VERIFIED LIVE
1. `backend/app/core/logging.py` — structured JSON logging
2. `backend/app/middleware/metrics.py` — MetricsMiddleware
3. `backend/app/api/v1/endpoints/health.py` — GET /health live
4. `agents/broski-bot/src/cogs/ops_alerts.py` — Discord #ops-alerts
5. `monitoring/prometheus.yml` + `monitoring/grafana/dashboards/hypercode.json`
**Verified:** /health → ok ✅ | /metrics → full Prometheus output ✅ | <5ms latency ⚡

### Phase 6 ✅ DONE + VERIFIED LIVE (2026-04-13 17:59 BST)
**CLI commands in HyperAgent-SDK/cli/commands/:**
1. `status.js` — ✅ VERIFIED — hits /health, pretty coloured output
2. `logs.js` — ✅ VERIFIED — GET /api/v1/logs?limit=N → 200 {logs:[], total:0}
3. `tokens.js` — ✅ VERIFIED — POST /api/v1/economy/award-from-course
4. `agents.js` — ✅ VERIFIED — healer-agent, hypercode-core, celery-worker online
5. `graduate.js` — ✅ VERIFIED — POST /api/v1/graduate/trigger

**Logs routing fix (2026-04-13):**
- Root cause: `dashboard.py` GET /logs (JWT-gated, Tasks table) shadowing `logs_broadcaster.py` GET /logs
- Fix: moved `logs_broadcaster.router` include BEFORE `dashboard_compat` in api.py
- Result: `curl http://localhost:8000/api/v1/logs?limit=10` → 200 `{"logs":[],"total":0}` ✅

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
- **Dockerfiles:** ALWAYS include apt-get upgrade + pip upgrade — see Phase 7 above

---

## Paths (copy-paste ready)

```powershell
# HyperAgent-SDK (CLI lives here!)
cd "H:\HyperAgent-SDK"

# HyperCode V2.4 (Docker + API)
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# Hyper-Vibe-Coding-Course (Supabase + Vercel)
cd "H:\the hyper vibe coding hub"

# Docker
docker compose up -d
docker compose exec api alembic upgrade head
docker compose logs api --tail 50

# CLI (run from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js logs --tail 20
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100

# Security scanning (run from H zone-V2.4)
docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet hypercode-v24-agent-x
```

---

## npm / SDK Quick Reference

```powershell
npx @w3lshdog/hyper-agent validate .agents/my-agent/
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

---

## BROski$ Token Economy (Course side)

- `public.users.broski_tokens` — balance column
- `token_transactions` — append-only ledger with idempotency guards
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only
- `shop_items` + `shop_purchases` — JSONB metadata fields
- `shop_purchases.item_slug` — used to filter for "agent-sandbox-access"
- Stripe integration for token packs (Starter/Builder/Hyper)
