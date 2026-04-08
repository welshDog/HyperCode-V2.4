## 🧠 CONTEXT: HyperCode V2.0 — BROski$ Token System Build Brief
Date: 2026-03-16
Repo: https://github.com/welshDog/HyperCode-V2.0
Stack: FastAPI + PostgreSQL + Redis + Celery + Docker Compose

---

## 🏗️ CURRENT SYSTEM STATE (as of today)

### What's running and healthy:
- Core API (FastAPI) — port 8000 ✅
- PostgreSQL + Redis — stable ✅
- Celery task pipeline — end-to-end proven ✅
- Mission Control Dashboard — port 8088 ✅
- Hyper-Mission UI — port 8099 ✅
- Healer Agent — port 8010 ✅
- Crew Orchestrator — port 8081 ✅
- Grafana/Prometheus/Loki/Tempo — port 3001 ✅
- Tests: 87 Core passed + 15 Mission passed ✅
- Auth: JWT-based, working through Core API

### Core API structure (backend/app/):
- models/ — SQLAlchemy ORM models (Postgres)
- schemas/ — Pydantic v2 schemas
- routers/ — FastAPI route handlers
- core/ — config, database, security, telemetry
- workers/ — Celery task workers
- services/ — business logic layer

### DB migrations: Alembic (backend/alembic/)
- Initial schema migration exists: 0b8c1f7f3f0b_initial_schema.py
- Pattern: always add new models via Alembic migration

---

## 🎯 WHAT WE'RE BUILDING: BROski$ Token System v1

### Purpose:
A gamification and motivation engine — neurodivergent-first.
Rewards users with BROski$ coins + XP for completing tasks, 
running missions, achieving milestones, and using the system.

### Why it matters:
- Core differentiator for HyperCode's neurodivergent-first mission
- Keeps users (especially ADHD brains) engaged and motivated
- Feeds into the future Evolutionary Pipeline (agents earn coins too)
- Unlocks: achievements, power-ups, leaderboards (Phase 2+)

---

## 📦 REQUIRED v1 COMPONENTS

### 1. Database Models (SQLAlchemy + Alembic migration)
- `BROskiWallet` — per-user coin + XP ledger
  - user_id (FK to users), coins (int), xp (int), level (int)
  - created_at, updated_at
- `BROskiTransaction` — immutable audit log
  - wallet_id (FK), amount (int), type (enum: earn/spend/bonus)
  - reason (str), metadata (JSON), created_at
- `BROskiAchievement` — achievement definitions
  - slug (unique), name, description, xp_reward, coin_reward, icon
- `BROskiUserAchievement` — which user has earned which achievement
  - wallet_id, achievement_slug, earned_at

### 2. Service Layer (backend/app/services/broski_service.py)
- `award_coins(user_id, amount, reason)` — add coins + log transaction
- `award_xp(user_id, amount, reason)` — add XP, check level up
- `spend_coins(user_id, amount, reason)` — deduct with balance check
- `get_wallet(user_id)` — return wallet state
- `check_and_award_achievements(user_id)` — evaluate + award earned badges
- `get_leaderboard(limit=10)` — top wallets by coins + XP

### 3. API Router (backend/app/routers/broski.py)
- GET  /broski/wallet          — my wallet (coins, XP, level)
- GET  /broski/transactions    — my transaction history (paginated)
- GET  /broski/achievements    — all available achievements
- GET  /broski/achievements/me — my earned achievements
- GET  /broski/leaderboard     — top 10 players
- POST /broski/award           — admin/agent endpoint: award coins/xp
(all endpoints protected by existing JWT auth)

### 4. Event Hooks — wire into existing system
- Task completed → +10 coins, +25 XP
- Task created → +2 coins
- Mission started → +5 coins
- Daily login → +5 coins (once per 24h)
- First task of the day → +15 XP bonus
- Achievement unlocked → bonus coins per achievement definition

### 5. Level System
XP thresholds (simple v1):
- Level 1: 0 XP      (BROski Recruit)
- Level 2: 100 XP    (BROski Cadet)
- Level 3: 250 XP    (BROski Agent)
- Level 4: 500 XP    (BROski Operator)
- Level 5: 1000 XP   (BROski Commander)
- Level 6: 2000 XP   (BROski Architect)
- Level 7: 5000 XP   (BROski Legend ♾️)

### 6. Seed Achievements (v1 starter set)
- `first_blood`     — Complete your first task (+50 XP, +20 coins)
- `streak_3`        — 3 tasks in one day (+100 XP, +30 coins)
- `mission_launch`  — Start your first mission (+75 XP, +25 coins)
- `hyperfocus_hero` — 5 tasks in one session (+150 XP, +50 coins)
- `early_bird`      — Complete a task before 9 AM (+30 XP, +10 coins)

---

## 🔧 TECH CONSTRAINTS

- Python 3.12, FastAPI, SQLAlchemy 2.x (async), Pydantic v2
- Alembic for ALL schema changes (never edit tables directly)
- Redis available for caching wallet state (optional optimisation)
- Celery available for async award jobs if needed
- Follow existing router pattern: see backend/app/routers/tasks.py
- Follow existing model pattern: see backend/app/models/task.py
- Follow existing service pattern: see backend/app/services/
- All endpoints require JWT auth (see backend/app/core/security.py)
- Tests go in backend/tests/ — follow existing test patterns
- Neurodivergent-friendly error messages (plain English, no blame)

---

## 📁 FILES TO CREATE

1. backend/app/models/broski.py          — ORM models
2. backend/app/schemas/broski.py         — Pydantic schemas
3. backend/app/services/broski_service.py — business logic
4. backend/app/routers/broski.py         — API endpoints
5. backend/alembic/versions/XXX_broski_token_system.py — migration
6. backend/tests/test_broski.py          — test suite
7. docs/guides/BROSKI_TOKEN_SYSTEM.md    — user guide

## FILES TO MODIFY

1. backend/app/main.py                   — register broski router
2. backend/app/routers/tasks.py          — add award hooks on task complete/create
3. backend/app/models/__init__.py        — add broski models to exports

---

## ✅ DEFINITION OF DONE

- [ ] All 4 DB models created + Alembic migration runs cleanly
- [ ] Service layer: all 6 functions implemented + tested
- [ ] All 6 API endpoints working with JWT auth
- [ ] Event hooks: task complete/create fires coin awards
- [ ] Level-up logic triggers on XP milestones
- [ ] 5 seed achievements defined + check logic implemented
- [ ] Tests: minimum 15 passing tests covering wallet, transactions, achievements
- [ ] Docs guide written in ADHD-friendly format
- [ ] Router registered in main.py
- [ ] No regressions in existing 87 Core tests

---

## 🧠 STYLE NOTES (neurodivergent-first)

- Error messages: "Not enough BROski$ coins — you need X more!" (not "insufficient funds")
- Level up message: "LEVEL UP BROski! You're now a [Level Name]! 🔥"
- Achievement message: "Achievement unlocked: [Name]! [Description] 🏆"
- Keep API responses human-readable with a `message` field alongside data
- Celebrate in logs too: logger.info("🔥 BROski$ awarded: +%d coins to user %s", amount, user_id)
