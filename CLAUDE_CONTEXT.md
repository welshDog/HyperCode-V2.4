# 🤖 HyperAgent-SDK + Hyperfocus Zone — Claude Context Handoff
> Read this first. Every word. Then start the mission.

---

## Who You're Talking To
- **Lyndz** aka BROski♾ (GitHub: @welshDog, npm: @w3lshdog) — South Wales
- Autistic + dyslexic + ADHD — chunked output, quick wins first, no waffle
- Windows primary (PowerShell), WSL2 + Raspberry Pi + Docker secondary
- Call them "Bro" — that's how we roll

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

## 6-Phase Roadmap — ALL COMPLETE 🏆

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| 6 | Terminal Tools | ✅ DONE + VERIFIED LIVE |

---

## ✅ What's Done — Full History

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
4. `supabase/functions/graduate-student/index.ts` — fires on graduation_events INSERT
5. Router wired in `backend/app/api/api.py` — /graduate tag
**Migration fix:** down_revision corrected to '005_add_access_provisions' — ran clean 003→004→005→006
**Table confirmed:** public.graduation_events ✅
**Endpoint live:** POST /api/v1/graduate/trigger ✅

### Phase 5 ✅ DONE + VERIFIED LIVE
1. `backend/app/core/logging.py` — structured JSON logging
2. `backend/app/middleware/metrics.py` — MetricsMiddleware
3. `backend/app/api/v1/endpoints/health.py` — GET /health live
4. `agents/broski-bot/src/cogs/ops_alerts.py` — Discord #ops-alerts
5. `monitoring/prometheus.yml` + `monitoring/grafana/dashboards/hypercode.json`
6. Prometheus Instrumentator + OpenTelemetry + Redis metrics pipeline
**Verified:** /health → ok ✅ | /metrics → full Prometheus output ✅ | <5ms latency ⚡

### Phase 6 ✅ DONE + VERIFIED LIVE (2026-04-13 17:59 BST)
**CLI commands in HyperAgent-SDK/cli/commands/:**
1. `status.js` — ✅ VERIFIED — hits /health, pretty coloured output
2. `logs.js` — ✅ VERIFIED — GET /api/v1/logs?limit=N → 200 {logs:[], total:0}
3. `tokens.js` — ✅ VERIFIED — POST /api/v1/economy/award-from-course
4. `agents.js` — ✅ VERIFIED — healer-agent, hypercode-core, celery-worker online
5. `graduate.js` — ✅ VERIFIED — POST /api/v1/graduate/trigger

**Logs routing fix (2026-04-13):**
- Root cause: `dashboard.py` GET /logs (JWT-gated, Tasks table) was shadowing `logs_broadcaster.py` GET /logs (Redis, public) due to FastAPI first-match routing
- Fix: moved `logs_broadcaster.router` include BEFORE `dashboard_compat` in api.py
- Result: `curl http://localhost:8000/api/v1/logs?limit=10` → 200 `{"logs":[],"total":0}` ✅
- Empty array is correct — Redis key `hypercode:logs` populates once agents push via RPUSH

**Logs schema note:**
- Endpoint returns `{"logs": [{id, time, agent, level, msg}], "total": N}`
- CLI logs.js maps this correctly
- If bare array `[{timestamp, level, message}]` needed — add `?format=flat` alias

**Import bug fixed (2026-04-13):**
- `graduate.py` + `models/graduate.py` — `backend.app.*` → `app.*`
- `_HAS_PHASE234 = True` confirmed ✅

---

## 🚨 Known Rules (never re-debate these)

- **Docker imports:** `from app.X import Y` — NEVER `from backend.app.X import Y`
- **FastAPI routing:** First-match wins — public routes must be included BEFORE auth-gated compat routes
- **Alembic down_revision:** Must match EXACT revision string — not just the number
- **CLI folder:** All `hyper-agent` commands run from `H:\HyperAgent-SDK`
- **Logs empty on fresh boot:** Normal — Redis `hypercode:logs` populates as agents run
- Port convention: 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- Supabase schema ↔ V2.4 Postgres NEVER merge
- `.env` files, Discord tokens — never committed
- One bot: broski-bot. Old Replit bot = dead.
- API keys: `hc_` prefix + `secrets.token_urlsafe(32)`

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
