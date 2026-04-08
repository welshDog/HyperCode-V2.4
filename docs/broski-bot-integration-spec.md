# 🦅 BROski Bot — Complete Technical Integration Spec

**Version:** 4.1 | **Target System:** Auto Manager / BRO / MATE Discord Server | **Status:** Verified

## 🧬 Repository Overview
**BROski Bot v4.0** is a production-grade Python Discord bot built on `discord.py >= 2.4.0`. It utilizes a modular cog-based architecture with a FastAPI-ready service layer, PostgreSQL + Redis backend, and AI integration via PERPLEXITY + OpenAI.

**Repo Location:** `https://github.com/welshDog/BROski-Bot.git`

---

## 🗂️ Architecture Breakdown

### Core Structure
```text
BROski-Bot/
├── src/
│   ├── bot.py          ← Main bot class + event handling (Prometheus metrics integrated)
│   ├── main.py         ← Entry point
│   ├── cogs/           ← Feature modules (slash commands)
│   ├── services/       ← Business logic layer (Service Pattern)
│   ├── models/         ← SQLAlchemy ORM models (PostgreSQL)
│   ├── repositories/   ← DB access layer (Repo Pattern)
│   ├── agents/         ← AI agent integrations
│   ├── api/            ← FastAPI endpoints
│   ├── config/         ← Settings management
│   └── utils/          ← Helpers, formatters, validators
├── database/           ← SQLite fallback + migrations
├── alembic/            ← DB migration system
└── tests/              ← pytest suite
```

### 🎮 Cog Modules — Command Structure
All slash commands are loaded via the cog system.

| Cog Module | Commands | Purpose | Status |
| :--- | :--- | :--- | :--- |
| `economy.py` | `/balance`, `/give`, `/leaderboard` | BROski$ token economy | ✅ Active |
| `focus.py` | `/focus start`, `/focus end` | ADHD focus sessions + XP | ⚠️ Needs Refactor |
| `quest_system.py` | `/quests`, `/quest accept` | Daily/legendary quests | ✅ Active |
| `profile_system.py` | `/profile`, `/rank` | User profiles, levels | ✅ Active |
| `shop_system.py` | `/shop`, `/buy` | BROski$ item shop | ✅ Active |
| `community.py` | `/announce`, `/event` | Community events | ✅ Active |
| `ai_relay.py` | `/ask`, `/brainstorm` | AI chat integration | ✅ Active |

**⚠️ Critical Note:** The `focus.py` cog currently uses a legacy `aiosqlite` implementation. It is disabled in `bot.py` by default. **Phase 1 of integration includes refactoring this to use the `FocusSession` SQLAlchemy model.**

### 🗄️ Database Schema (PostgreSQL v4.0)
20+ production tables with triggers and indexes.

*   **`users`**: Core user record (tokens, XP, level, risk_score).
*   **`economy`**: Token balances, daily streaks, lifetime stats.
*   **`transactions`**: Full audit trail of all BROski$ movements.
*   **`focus_sessions`**: ADHD timer sessions (active/completed).
*   **`quests`**: Quest definitions (Standard, Timed, Collaborative).
*   **`user_quests`**: Per-user quest progress tracker.
*   **`achievements`**: Unlockable badges and rewards.

---

## 🔐 Configuration & Dependencies

### Environment Variables (`.env`)
```bash
# Core
DISCORD_TOKEN=your_token_here
DISCORD_GUILD_ID=your_guild_id
LOG_LEVEL=INFO

# Database (PostgreSQL)
DATABASE_URL=postgresql://broski:password@localhost:5432/broski_db

# Cache (Redis)
REDIS_URL=redis://localhost:6379/0

# AI Services
PERPLEXITY_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# Feature Flags
ENABLE_AUTO_MODERATION=true
ENABLE_ANALYTICS=true
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8000
```

### Full Dependency Stack
*   **Runtime:** Python 3.11+
*   **Bot Framework:** `discord.py >= 2.4.0`
*   **Database:** `SQLAlchemy 2.0.23`, `asyncpg 0.29.0`
*   **Cache:** `redis 5.0.1`
*   **AI:** `PERPLEXITY`, `openai`
*   **Monitoring:** `prometheus-client`

---

## 🚀 Integration Plan — Auto Manager / BRO / MATE Server

### Phase 1: Infrastructure & Refactoring (Day 1-2)
1.  **Deploy Core Infrastructure:**
    *   Provision VPS (Ubuntu 20.04+, 4GB RAM).
    *   Run `docker-compose up -d` (Postgres, Redis, Bot).
2.  **Refactor Focus Cog:**
    *   Update `src/cogs/focus.py` to remove `aiosqlite`.
    *   Inject `FocusService` to handle DB operations via `src/models/FocusSession`.
    *   Uncomment `"src.cogs.focus"` in `bot.py`.

### Phase 2: Server Configuration (Day 3)
**Role Hierarchy Setup:**
1.  🦅 **BROski Bot** (Highest Managed Role)
2.  👑 **Admin**
3.  🛡️ **Moderator** (BRO+)
4.  ⭐ **Level 10+** (Auto-assigned)
5.  🎯 **Hyperfocus Member**
6.  🌱 **New MATE** (Default)

**Channel Rules:**
*   `#welcome`: Bot greets with `/profile` tip.
*   `#broski-bank`: Economy commands only.
*   `#hyperfocus-zone`: Focus session start/end logs.
*   `#quests`: Daily quest reset announcements (00:00 UTC).

### Phase 3: Moderation & Economy (Day 4)
1.  **Toxicity Detection:**
    *   Enable `message_analytics` table.
    *   Set threshold: Score > 0.75 = Auto-warn.
2.  **Economy Rates:**
    *   Start Balance: 1000 BROski$.
    *   Daily Claim: +25 BROski$ (Streak multiplier x1.1).
    *   Focus Session: +50 BROski$ per 25 mins.

---

## 🧪 Testing Procedures

### Unit Tests
Run the pytest suite to verify logic, especially the refactored Focus engine.
```bash
python -m pytest tests/ -v --asyncio-mode=auto
```

### Integration Checklist
- [ ] `/balance` returns 1000 for new user.
- [ ] `/focus start` creates a row in PostgreSQL `focus_sessions` table.
- [ ] `/give` transfers tokens correctly and logs to `transactions`.
- [ ] AI Chat `/ask` returns response from PERPLEXITY/OpenAI.

### Load Testing
- Simulate 20 concurrent slash commands.
- Monitor Redis cache hit rate via Prometheus (localhost:8000).

---

## 💾 Backup & Rollback

### Backup Strategy
*   **Automated:** Daily cron job dumps PostgreSQL to S3/Local `backups/`.
*   **Retention:** 7 Daily, 4 Weekly.

### Rollback Plan
If deployment fails:
1.  `docker-compose down`
2.  Revert to last stable git tag: `git checkout tags/v3.9.0`
3.  Restore DB if schema corrupted: `psql broski_db < backups/pre_deploy.sql`
4.  `docker-compose up -d`

---

## ⚠️ Risk Assessment

| Risk | Likelihood | Mitigation |
| :--- | :--- | :--- |
| **Focus Cog DB Conflict** | High | **Strict Refactor:** Ensure `focus.py` uses ORM before enabling. |
| **Discord Rate Limits** | Medium | Redis caching implemented for profile/balance checks. |
| **AI Cost Overrun** | Low | Hard cap set in OpenAI/PERPLEXITY dashboard. |

---

**🔥 BROski Power Level:** FULL AUTO-MANAGER ARCHITECT 🦅💜
