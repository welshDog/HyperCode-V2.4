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
| **3** | **Agent Access + Shop Bridge** | **👈 CURRENT MISSION** |
| 4 | npm run graduate 🔥 | 🔜 |
| 5 | Observability | 🔜 |
| 6 | Terminal Tools Integration | 🔜 |

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

### Bot Consolidation ✅ DONE
- Old Replit bot stopped + token reset
- `broski-bot` (HyperCode V2.4, Docker) is the ONE BOT

---

## 🎯 CURRENT MISSION — Phase 3: Agent Access + Shop Bridge

**Goal:** Buy item in Course shop → get real V2.4 sandbox access automatically.

**Architecture:**
```
Course: student buys "Agent Sandbox Access" (300 tokens)
        ↓
Course: shop_purchases INSERT → provision-access edge function fires
        ↓
V2.4: POST /api/v1/access/provision
      (deduped via source_id)
      generates api_key, stores access_provisions record
      sends Discord DM via Discord HTTP API
        ↓
Student receives DM: { api_key, mission_control_url }
```

**New table needed in V2.4:**
```sql
CREATE TABLE access_provisions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  discord_id VARCHAR(32),
  api_key TEXT UNIQUE NOT NULL,       -- hc_ prefixed, urlsafe(32)
  provision_type VARCHAR(64),         -- 'agent_sandbox'
  source_id TEXT UNIQUE,              -- idempotency key = shop_purchases.id
  mission_control_url TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP                -- NULL = no expiry
);
```

**Files to build:**
1. V2.4 migration — `005_add_access_provisions.py`
2. V2.4 `AccessProvision` ORM model (in `backend/app/models/models.py`)
3. V2.4 `backend/app/api/v1/endpoints/access.py` — POST /api/v1/access/provision
4. V2.4 config — SHOP_SYNC_SECRET, DISCORD_BOT_TOKEN, MISSION_CONTROL_URL
5. Course `supabase/functions/provision-access/index.ts` — fires on shop_purchases INSERT
6. Wire router in `backend/app/api/api.py`

**Done when:** Buy "Agent Sandbox Access" in course shop → Discord DM arrives with `api_key` + `mission_control_url` ✅

**Critical:** Same source_id dedup pattern as Phase 2. Same X-Sync-Secret auth.

---

## Key Technical Decisions (don't re-debate these)

- Port convention: 3100-3199 writing, 3200-3299 code, 3300-3399 data, 3400-3499 discord, 3500-3599 automation
- `mcp_compatible: true` requires `port` — enforced in spec
- Supabase schema ↔ V2.4 Postgres NEVER merge — incompatible tooling
- `.env` files, Discord tokens — never committed, never merged
- `apps/web/` — archived, never migrated
- Windows PowerShell first, bash second — always
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
- One bot: broski-bot. Old Replit bot = dead.
- Discord DM delivery: V2.4 endpoint calls Discord HTTP API directly (bot token in settings, no extra pub/sub)
- API keys: `hc_` prefix + `secrets.token_urlsafe(32)` — 43 chars, URL-safe

---

## Paths (copy-paste ready)

```powershell
# HyperAgent-SDK
cd "H:\HyperAgent-SDK"

# HyperCode V2.4
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4\backend"

# Hyper-Vibe-Coding-Course
cd "H:\the hyper vibe coding hub"

# V2.4 Docker commands
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api alembic history --verbose
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
