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

## 6-Phase Roadmap — Current Status

| Phase | Name | Status |
|---|---|---|
| 0 | Hard Conflict Fixes | ✅ DONE |
| 1 | Identity Bridge | ✅ DONE + VERIFIED LIVE |
| 2 | Token Sync | ✅ DONE + VERIFIED LIVE |
| 3 | Agent Access + Shop Bridge | ✅ DONE + VERIFIED LIVE |
| 4 | npm run graduate 🔥 | ✅ DONE + VERIFIED LIVE |
| 5 | Observability | ✅ DONE + VERIFIED LIVE |
| **6** | **Terminal Tools** | **🚧 IN PROGRESS — 4/5 commands working** |

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

### Phase 5 ✅ DONE + VERIFIED LIVE (2026-04-13)
1. `backend/app/core/logging.py` — structured JSON logging, called at startup
2. `backend/app/middleware/metrics.py` — MetricsMiddleware wired into main.py
3. `backend/app/api/v1/endpoints/health.py` — GET /health live
4. `agents/broski-bot/src/cogs/ops_alerts.py` — polls /health every 5 mins, fires #ops-alerts
5. `monitoring/prometheus.yml` — scrape config
6. `monitoring/grafana/dashboards/hypercode.json` — dashboard provisioned
7. Prometheus Instrumentator + OpenTelemetry wired in main.py
8. Redis metrics pipeline — req counts, response times, error counts per minute
9. Agent heartbeat loop — hypercode-core publishes to Redis every 10s
**Verified 2026-04-13 16:18 BST:**
- `curl http://localhost:8000/health` → `{"status":"ok"}` ✅
- `curl http://localhost:8000/metrics` → Full Prometheus output ✅
- All /health responses under 5ms ⚡

### Phase 6 🚧 IN PROGRESS (2026-04-13)
**CLI files pushed to HyperAgent-SDK:**
1. `cli/commands/status.js` — ✅ WORKING
2. `cli/commands/logs.js` — 🔧 needs /api/v1/logs endpoint built in V2.4
3. `cli/commands/tokens.js` — ✅ WORKING (after import fix below)
4. `cli/commands/agents.js` — ✅ WORKING — shows healer-agent, hypercode-core, celery-worker online
5. `cli/commands/graduate.js` — ✅ WORKING (after import fix below)
6. `cli/index.js` — updated, all 5 commands registered

**Import bug found + fixed 2026-04-13 17:29 BST:**
- `backend/app/api/v1/endpoints/graduate.py` lines 8-11 — `from backend.app.db.*` → `from app.db.*`
- `backend/app/models/graduate.py` line 2 — `from backend.app.db.base` → `from app.db.base`
- economy.py and access.py were already correct
- `_HAS_PHASE234 = True` confirmed in running process ✅
- `POST /api/v1/economy/award-from-course` → 422 (route registered, Pydantic validation firing) ✅

**Remaining for Phase 6 completion:**
- Build `GET /api/v1/logs?tail=N` endpoint in V2.4 (logs_broadcaster.py or new endpoint)
- `node cli/index.js logs --tail 10` — currently 404

### Bot Consolidation ✅ DONE
- Old Replit bot stopped + token reset
- `broski-bot` (HyperCode V2.4, Docker) is the ONE BOT

---

## ⚠️ Known Issues / Rules (never re-debate these)

- **Docker imports:** Always use `from app.X import Y` — NEVER `from backend.app.X import Y` inside container
- **Alembic down_revision:** Must match EXACT revision string in previous migration file — not just the number
- **CLI folder:** `hyper-agent` commands run from `H:\HyperAgent-SDK` — NOT from HyperCode-V2.4
- **Tokens 404:** If discord_id isn't linked to a V2.4 user — expected, not a bug
- **logs CLI:** Needs `GET /api/v1/logs?tail=N` endpoint built — Phase 6 remaining task
- Port convention: 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- `mcp_compatible: true` requires `port` — enforced in spec
- Supabase schema ↔ V2.4 Postgres NEVER merge — incompatible tooling
- `.env` files, Discord tokens — never committed, never merged
- `apps/web/` — archived, never migrated
- Windows PowerShell first, bash second — always
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
- One bot: broski-bot. Old Replit bot = dead.
- API keys: `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars, URL-safe

---

## Paths (copy-paste ready)

```powershell
# HyperAgent-SDK (CLI lives here!)
cd "H:\HyperAgent-SDK"

# HyperCode V2.4 (Docker + API)
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# Hyper-Vibe-Coding-Course (Supabase + Vercel)
cd "H:\the hyper vibe coding hub"

# V2.4 Docker commands
docker compose up -d
docker compose exec api alembic upgrade head
docker compose logs api --tail 50

# CLI commands (run from H:\HyperAgent-SDK)
$env:HYPERCODE_API_URL = "http://localhost:8000"
node cli/index.js status
node cli/index.js agents list
node cli/index.js tokens award <discord_id> <amount>
node cli/index.js graduate <discord_id> --tokens 100
node cli/index.js logs --tail 10
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
