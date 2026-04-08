# BROski Bot v3.0 Code Review and HyperFocus Zone Design

## 1. Repository State Overview

The BROski-Bot repository currently contains two overlapping architectures:

- A **working v3-style bot** built around `bot.py` plus flat cogs `economy.py` and `focus_engine.py`, using SQLite via `aiosqlite` and discord.py hybrid commands.[^1]
- A partially implemented **v4-style layered architecture** (`broski_database.py`, `broski_models.py`, `broski_services.py`, `broski_repositories.py`, `broski_settings.py`, `broski_logging.py`, `broski_tests.py`, refactor docs), which references a `src/` package and PostgreSQL/Redis but is not wired up or complete.

The docs (`README.md`, `QUICKSTART.md`, `PROJECT_STRUCTURE.md`, `🎯 BROski-Bot Implementation Roadmap.md`, `broski_refactor_plan.txt`) describe a more advanced structure (src/, tests/, docs/, database/, CI, Docker, metrics) that does not yet exist in the filesystem, so the repository is in a **transition state** between prototype and production design.[^1]

## 2. Codebase Structure Analysis

### 2.1 Actual runtime structure (v3)

Key runtime files:

- `bot.py`: Discord bot entrypoint, logging setup, database bootstrap, cog loading, info and help commands.
- `economy.py`: Economy cog providing `/balance`, `/daily`, `/give`, `/leaderboard` commands using SQLite and `aiosqlite`.
- `focus_engine.py`: Focus cog providing `/focus` and `/focusend` commands, managing active sessions in-memory and persisting sessions and rewards.
- `requirements.txt`, `docker-compose.yml`, `Dockerfile`, `env.example`: deployment and configuration support.[^1]

Characteristics:

- **Flat layout**: all code is at repo root, no `src/` package or `cogs/` package directory even though `bot.py` tries to load `cogs.economy`, `cogs.focus_engine`, etc.
- **Tight coupling**: command handlers directly touch the database schema with raw SQL, and business rules (e.g., rewards, streaks) live inside cog methods.
- **SQLite-first**: `bot.py` creates tables via `aiosqlite`, not via migrations or SQLAlchemy models.

### 2.2 Aspirational v4 architecture

The `broski_*` files and refactor documents describe a much more modular architecture:

- **Config layer**: `broski_settings.py` uses Pydantic Settings to strongly-type environment configuration (Discord, DB, Redis, economy and focus tuning, rate limits, logging, Sentry, Prometheus).
- **Database layer**: `broski_database.py` defines an async SQLAlchemy engine + session factory with pooling, Base model, table (create/drop), and health checks.
- **Domain models**: `broski_models.py` defines `User`, `Economy`, `FocusSession`, `Quest`, `UserQuest` etc. with relationships and timestamps.
- **Repository layer**: `broski_repositories.py` implements a generic `BaseRepository` plus `UserRepository`, `EconomyRepository`, `FocusSessionRepository` (CRUD, leaderboards, active-session queries).
- **Service layer**: `broski_services.py` implements `EconomyService` and `FocusService` as business-logic orchestration over repositories (daily rewards, transfers, focus reward calculations).
- **Infrastructure**: `broski_logging.py` configures structlog-based structured logging with app context; `broski_exceptions.py` defines rich domain exceptions; `broski_tests.py` embeds pytest fixtures and unit/integration tests for the service layer; `broski_refactor_plan.txt` and `🎯 BROski-Bot Implementation Roadmap.md` contain an 8+ week roadmap toward this architecture.

Issues:

- These modules import from `src.config`, `src.core`, `src.models`, `src.services`, `src.repositories`, which do not yet exist as a real package.
- Several files are truncated or contain duplicated/incomplete definitions (e.g., `EconomyRepository.get_leaderboard` duplicated, partial methods cut off mid-line).
- There is no `tests/` directory; test code lives inside `broski_tests.py` but references the non-existent `src.` package.

Result: the v4 stack is an excellent design blueprint, but **not yet runnable**.

## 3. Dependency and Infrastructure Audit

### 3.1 Python dependencies

From `requirements.txt`:

- `discord.py>=2.4.0` – modern Discord library with slash/hybrid commands.
- `python-dotenv>=1.0.0` – environment loading for local `.env` files.
- `aiosqlite>=0.19.0` – async access to SQLite database.
- `aiohttp>=3.9.0` – HTTP client (currently not used in core cogs).
- `cryptography>=41.0.0` – crypto primitives (not yet used in v3 runtime).
- `Pillow>=10.0.0` – image processing (unused in current core files).
- `pytest`, `pytest-asyncio` – test framework (used by design in `broski_tests.py`).
- `prometheus-client>=0.18.0` – metrics (wired in v4-style `BroskiBot` class, not in v3 `bot.py`).
- `redis>=5.0.0` – for rate limiting / caching as per settings, not used in v3 runtime.

Observations:

- Several deps (cryptography, Pillow, Redis, Prometheus) are present to support planned features (image generation, secure storage, rate limiting, metrics) but **not yet wired into the live entrypoint**.
- Dependency versions are specified with `>=`, which eases upgrades but increases the risk of breaking changes or supply-chain surprises over time; production deployments should prefer **pinned versions** with periodic review.

### 3.2 Environment and deployment

- `env.example` documents the main configuration knobs: Discord token, DB path, MintMe API, Redis URL, Prometheus port, log level, debug flag.[^1]
- `Dockerfile` is simple: install requirements, copy repo, create `logs` and `database` directories, and run `python bot.py`.
- `docker-compose.yml` defines a `broski-bot` service and a `redis` service on a shared bridge network; volumes mount `database/`, `logs/`, and `backups/` from the host.

Strengths:

- Docker + compose gives straightforward local and single-node production deployment.
- Volumes ensure persistence for DB and logs.

Gaps:

- No healthcheck configuration for the container.
- No automated DB migrations; schema is created ad-hoc by `bot.py`.
- No environment-specific overrides (dev vs prod) or secrets tooling.

## 4. Security Assessment

### 4.1 Token and secrets handling

- Discord bot token is loaded from `.env` using `python-dotenv`, which is standard for development but not ideal for production.
- There is currently **no `.gitignore` or `.dockerignore` in the repo**, so `.env`, logs and the SQLite database are at risk of being accidentally committed or included in Docker build contexts if added locally.

Recommendations:

- Add a robust `.gitignore` (env files, database files, logs, caches, `__pycache__`, etc.).
- Add `.dockerignore` to exclude `.git`, tests, docs, local venv, and any secrets.
- For production, load secrets via environment variables or a secrets manager instead of keeping a long-lived `.env` on disk.

### 4.2 Database and query safety

- All SQL in `economy.py` and `focus_engine.py` uses parameterized queries with `?` placeholders, so there is **no direct SQL injection risk** from user input in the current code.
- The leaderboard query dynamically injects the column name via an f-string, but the column name is chosen from a fixed mapping (`field_map`), not directly from user input, so this is safe.
- SQLite is file-based; the default DB path is under `database/broski_main.db` with host-mounted volume, so file permissions on the host and container matter for confidentiality (user IDs, usernames, optional wallet addresses).

Enhancements:

- Encrypt sensitive fields like `wallet_address` with `cryptography` before storing, as already anticipated by the dependency list.
- Move to PostgreSQL with proper access controls in the v4 rollout, as planned in `broski_refactor_plan.txt`.

### 4.3 Permissions and abuse resistance

- `bot.py` enables `Intents.all()`, which is convenient but grants more access than strictly needed (e.g., all guild and member events). Least-privilege would suggest enabling only the intents actually used (guilds, members, message content, reactions if needed).
- There is no in-bot **rate limiting** on commands yet, so a malicious or buggy client could spam `/daily`, `/balance`, `/focus`, etc., consuming resources (DB connections, logging) and generating noisy logs.
- No anti-abuse controls on `/give` beyond balance checks; in a multi-guild deployment, there is no concept of per-guild limits or moderator approval for large transfers.

Mitigations (short term):

- Restrict intents to only those required in `bot.py` (guilds, members, message content).
- Use discord.py built-in cooldown decorators (e.g., `@commands.cooldown`) on economy and focus commands to limit spam.
- Add a simple permission check (e.g., manage_guild or a custom role) for high-risk commands such as large `/give` amounts.

### 4.4 Logging and privacy

- `bot.py` logs to both stdout and `logs/broski_bot.log`, including basic startup and guild count info.
- The v4 logging module (`broski_logging.py`) will add structured, JSON-friendly logs with rich context (app name, version, environment), which is well-suited for production but currently unused.

Recommendation:

- Gradually replace `logging.basicConfig` in `bot.py` with `configure_logging()` from `broski_logging.py` once the `src.config.settings` module is in place.
- Define a log retention policy and rotate logs (via Docker log driver, external log collector, or Python handlers).

## 5. Performance and Scalability

### 5.1 Command performance

- Each economy/focus command opens a **new `aiosqlite` connection** via `aiosqlite.connect(DB_PATH)`. For a small community bot this is acceptable, but under heavier load, connection reuse and a small pool would be preferable.
- Leaderboard queries select up to 10 rows ordered by a simple numeric column with a WHERE on `is_active = TRUE`; performance is fine for typical Discord server sizes.

Potential bottlenecks:

- SQLite itself is a single-file DB with a writer lock. High write frequency (many `/daily`, `/give`, `/focusend`) might lead to lock contention.
- Logging all events to disk could become I/O-heavy at scale.

Planned improvements (via v4 stack):

- Switch to PostgreSQL with asynchronous SQLAlchemy and connection pooling (`broski_database.py`).
- Introduce an in-memory cache (Redis) for hot queries like leaderboards and quick balance lookups.
- Use Prometheus (`prometheus-client`) to track command counts, durations, and error rates, then use those metrics to guide scaling decisions.

## 6. Code Quality and Documentation

### 6.1 Code style and structure

Current v3 files (`bot.py`, `economy.py`, `focus_engine.py`):

- Use clear, descriptive docstrings at the module and function level.
- Mostly follow PEP 8 with readable variable names and logical flow.
- Use type annotations only sparsely (parameters and return types are generally un-annotated).
- Command handlers are relatively small and readable but bundle database, validation, and presentation logic together.

The v4 service/repository/model modules:

- Have strong type hints, docstrings, and clear separation of concerns.
- Use well-structured logging via `LoggerMixin`.
- Introduce domain-specific exceptions for clear error semantics.

Gaps:

- Truncations and duplicated definitions (e.g., incomplete method bodies) mean the v4 code cannot compile yet.
- There is no automated formatting or linting configuration in the repo (e.g., Black, Ruff, or isort configs).

### 6.2 Documentation

Documentation assets include:

- `README.md`: overview, feature list, quick-start, commands, tech stack, high-level architecture sketch.[^1]
- `QUICKSTART.md`: detailed Docker and bare-metal setup steps, first commands, monitoring pointers.[^1]
- `PROJECT_STRUCTURE.md`: aspirational structure diagram and implementation status table.
- `🎯 BROski-Bot Implementation Roadmap.md` and `broski_refactor_plan.txt`: detailed multi-phase refactor and deployment plan.

These provide **excellent high-level orientation**, but they **do not accurately describe the currently committed directory structure**, which can confuse contributors.

Recommendations:

- Add a short section to `README.md` clarifying the current state (v3 runtime vs v4 plan) and how to run the stable version.
- Move detailed refactor plans under `docs/` once that directory exists; keep `README.md` focused on user-facing info.

## 7. Testing and CI/CD

### 7.1 Present test situation

- There is no `tests/` directory and no test runner configuration in the root.
- The `broski_tests.py` file contains:
  - Pytest fixtures for async SQLAlchemy sessions.
  - Unit tests for `EconomyService` (daily rewards, transfers, error cases).
  - Integration tests for economy flows.
- These tests reference `src.core.database`, `src.models`, and `src.services` and cannot be executed against the current root-level v3 architecture.

### 7.2 Recommendations

Short term (for the v3 code):

- Create `tests/` and move/rename the v3-relevant parts into real test modules:
  - `tests/test_economy_cog.py` using `aiosqlite` against an in-memory DB to test `/daily`, `/give`, `/leaderboard`.
  - `tests/test_focus_engine_cog.py` to test `/focus` and `/focusend` flows.
- Add a simple `pytest.ini` and a `Makefile` or scripts for `make test`.

Medium term (as v4 matures):

- Finalize `src/` structure, then re-target `broski_tests.py` content into:
  - `tests/unit/test_economy_service.py` and `tests/unit/test_focus_service.py` for pure business logic.
  - `tests/integration/test_economy_flow.py` for DB-backed flows using PostgreSQL test instances.
- Add GitHub Actions `ci.yml` per the roadmap to run linting, tests, and Docker builds on push/PR.

## 8. Architectural Improvement Recommendations

### 8.1 Short-term (stabilize v3)

1. **Finish and fix existing runtime code**
   - Complete `economy.py` (file is currently truncated at the end of `leaderboard` command).
   - Add missing `return` and final embed logic for the "no rows" case in `leaderboard`.
   - Ensure `focus_engine.py` is fully wired and imported from the same DB schema that `bot.py` initializes.

2. **Align module paths with `bot.py`**
   - Create a `cogs/` directory and move:
     - `economy.py` → `cogs/economy.py`.
     - `focus_engine.py` → `cogs/focus_engine.py`.
   - Add `cogs/__init__.py` and update any relative imports if needed.

3. **Add basic safety controls**
   - Apply `@commands.cooldown(1, 3, commands.BucketType.user)` to economy/focus commands to prevent spam.
   - Add simple permission checks on `/give` for large transfers (e.g., require `manage_guild` or a "BROski Overlord" role above a threshold).

4. **Harden deployment hygiene**
   - Add `.gitignore` and `.dockerignore` per `PROJECT_STRUCTURE.md`.
   - Document recommended `.env` handling for production (external secrets).

### 8.2 Medium-term (bridge to v4)

1. **Introduce `src/` packaging without changing runtime behavior**
   - Create `src/` and move `bot.py` → `src/bot.py`; change Docker `CMD` to `python -m src.bot`.
   - Add `src/cogs/` and move cogs accordingly; adjust `bot.py` extension names to `src.cogs.economy`, etc.

2. **Adopt Pydantic settings and structured logging**
   - Implement `src/config/settings.py` based on `broski_settings.py`, starting with only fields needed by v3.
   - Replace `logging.basicConfig` with `configure_logging()` from `broski_logging.py`, minimally adapted to `src.config.settings`.

3. **Wrap SQLite access behind a thin repository/service layer**
   - Implement small `EconomyRepository` and `FocusSessionRepository` over `aiosqlite` for the existing schema.
   - Extract business logic from `economy.py` and `focus_engine.py` into `services`, then call those services from the cogs.

4. **Gradually align schema with SQLAlchemy models**
   - Introduce SQLAlchemy models in `src/models` mirroring the existing SQLite schema.
   - Use Alembic migrations to evolve toward the richer schema described in `broski_models.py`.

### 8.3 Long-term (full v4 and beyond)

- Migrate to PostgreSQL and Redis for persistence and caching.
- Deploy Prometheus + Grafana and Sentry using the v4 wiring.
- Implement AI Relay, quests, gig marketplace, and MintMe on top of the hardened service layer.
- Add a small HTTP API (FastAPI) for dashboards and external integrations (e.g., web-based focus analytics).

## 9. HyperFocus Zone – Technical Specification

### 9.1 Goals and user stories

Goals:

- Gamify deep work for neurodivergent users with clear rewards and feedback.
- Track focus behavior over time (sessions, streaks, hyperfocus milestones).
- Reduce Discord-driven distraction during focus sessions while remaining gentle and supportive.

Key user stories:

- “As a user, I want to start a focus session with a project name and duration so that I can commit to a block of work.”
- “As a user, I want the bot to reward me with tokens and XP when I complete a focus session, with extra rewards for longer or hyperfocus sessions.”
- “As a user, I want a dashboard that shows my total focus time, streaks, and best sessions so I can see my progress.”
- “As a user, I want the bot to nudge me when I start chatting off-topic during a focus session so I can return to my task.”

### 9.2 Data model

The existing SQLite schema already includes a `focus_sessions` table with:

- `session_id` (PK), `discord_id`, `project_name`, `start_time`, `end_time`, `duration_min`, `tokens_earned`, `completed`.

To support the advanced HyperFocus Zone, extend the schema with optional fields/tables:

- Add columns to `focus_sessions`:
  - `is_hyperfocus` BOOLEAN DEFAULT FALSE – mark sessions above the hyperfocus threshold.
  - `distraction_events` INTEGER DEFAULT 0 – count Discord nudges during session.
- Add a derived field to `users` (optional optimization):
  - `focus_score` INTEGER DEFAULT 0 – aggregated productivity metric.

Alternatively, create a `focus_session_events` table to log per-session events (distractions, manual breaks), but PoC can function with the simpler column-based approach.

### 9.3 Productivity tracking algorithms

Core measures:

- **Session duration**: total focused minutes per session.
- **Hyperfocus classification**: session is hyperfocus if `duration_min ≥ HYPERFOCUS_MIN` (e.g., 60 minutes, configurable).
- **Completion rate**: ratio of completed sessions vs. aborted/short sessions.
- **Streak**: number of consecutive days with at least one completed session.

Proposed `FocusScore` per user:

- Let:
  - \(M\) = total focus minutes.
  - \(H\) = count of hyperfocus sessions.
  - \(S\) = active focus streak (days).
  - \(D\) = total distraction events across sessions.
- Define a score:

\[
\text{FocusScore} = \lfloor \alpha \cdot \ln(1 + M) + \beta \cdot H + \gamma \cdot S - \delta \cdot D \rfloor
\]

with suggested weights (tunable via settings):

- \(\alpha = 5\) – overall minutes weight.
- \(\beta = 10\) – each hyperfocus session is a significant achievement.
- \(\gamma = 3\) – reward streak consistency.
- \(\delta = 1\) – mild penalty for distractions.

The PoC can compute this score on the fly from `focus_sessions` without storing it, and later cache it into `users.focus_score` for fast leaderboards.

### 9.4 Distraction-blocking mechanisms (Discord scope)

The bot cannot control OS-level distractions but can reduce Discord noise during active sessions:

1. **Focus mode presence**
   - When a session starts, set user-friendly presence text like "in HyperFocus Zone" for the bot, and optionally DM the user with quick setup tips (mute channels, enable DND).

2. **Channel distraction detection**
   - Add a `@commands.Cog.listener()` for `on_message` inside the focus cog.
   - If the author has an active session and posts in a non-whitelisted text channel, increment `distraction_events` for the active session and send a gentle embed:
     - "Hey BROski, you’re in a focus session on **{project}** – want to get back to it?"
   - Optionally provide quick reactions/buttons: `✅ Back to focus`, `⏸ Pause`, `🛑 End` (full interaction support can come later using discord.py UI components).

3. **Self-selected safe channels**
   - Add a `/focusconfig` command where users can configure:
     - Allowed channels during focus (e.g., #focus-room, DM with BROski-Bot).
     - Whether to receive nudges at all.
   - Store this in a simple `focus_user_settings` table keyed by `discord_id`.

4. **Gentle, neurodivergent-friendly behavior**
   - Never shame or hard-block; always frame nudges positively.
   - Provide clear options to snooze or disable nudges.

### 9.5 Focus session management

Enhance and standardize commands:

- `/focus start [project] [minutes]` – start a timed focus session.
  - If `minutes` omitted, default from user settings (e.g., 25).
  - Validate `minutes` against `focus_max_session_minutes` from settings.
- `/focus end` – end the current session early or on time.
- `/focus status` – show remaining time and current streak.
- `/focus stats [@user] [period]` – analytics dashboard for self or others.
- `/focus streak` – show current focus streak and best streak.

The PoC will primarily implement `/focus` (start), `/focusend` (end), and `/focusstats` (basic analytics) while leaving configuration and advanced events as extensions.

### 9.6 Progress analytics dashboard

The dashboard will be an embed-driven view, delivered by `/focusstats`:

For a chosen user and period (default last 30 days):

- Total completed sessions and total focus minutes.
- Average session length.
- Count of hyperfocus sessions.
- Current and best focus streak.
- FocusScore.
- A simple textual "graph" of recent days, e.g.:

```text
Last 7 days:
Mon ▓▓▓▓▓ 50m
Tue ▓▓▓ 30m
Wed ▓ 10m
Thu ▓▓▓▓▓▓ 70m (🔥)
Fri ▓▓ 20m
Sat —
Sun ▓▓▓ 30m
```

Future extension: export data for external dashboards (e.g., web or Grafana) using a small HTTP API.

### 9.7 Integration with existing bot features

- **Economy**: reuse `economy_transactions` and `users.total_focus_min` already in the schema. Each completed session:
  - Increments `total_focus_min` by `duration_min`.
  - Awards base reward + duration bonus tokens and XP, recorded via `economy_transactions`.
- **Leaderboards**: extend `/leaderboard` to support a `focus` category (already partly wired) that orders by `total_focus_min` or `FocusScore`.
- **Achievements**: later tie into the quest/achievement system (e.g., `LEGENDARY FOCUS` for 60+ minutes, `Streak Master` for 14+ days).

## 10. HyperFocus Zone – Proof-of-Concept Cog

Below is a PoC cog that can live at `cogs/focus_engine.py` in the v3 architecture. It refines the existing focus implementation with:

- Timed sessions with optional duration.
- Token and XP rewards with a duration bonus.
- Basic stats dashboard (`/focusstats`).
- Hook points for distraction tracking (commented for now).

```python
"""Advanced HyperFocus Engine Cog - PoC implementation.

Place this file at cogs/focus_engine.py and ensure `bot.py` loads `cogs.focus_engine`.
Relies on the existing SQLite schema created by bot.py, with an optional
`is_hyperfocus` column added to `focus_sessions`.
"""

import os
from datetime import datetime, timedelta

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

DB_PATH = os.getenv("DB_PATH", "database/broski_main.db")

# Tunable focus parameters (later move to settings/config)
BASE_REWARD = 200            # Tokens for any completed session
PER_MINUTE_BONUS = 2         # Extra tokens per minute of focus
HYPERFOCUS_THRESHOLD = 60    # Minutes required for a session to count as hyperfocus
HYPERFOCUS_MULTIPLIER = 1.5  # Multiplier applied when threshold reached
XP_PER_MINUTE = 5            # XP gained per minute of focus


class FocusEngine(commands.Cog):
    """HyperFocus session tracker with rewards and basic analytics."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # active_sessions[user_id] = {"start": datetime, "project": str, "duration": int | None}
        self.active_sessions: dict[int, dict] = {}

    async def _ensure_user_row(self, user_id: int, username: str) -> None:
        """Ensure the user exists in the users table."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO users (discord_id, username)
                VALUES (?, ?)
                """,
                (str(user_id), username),
            )
            await db.commit()

    async def _record_session(
        self,
        user_id: int,
        project: str,
        start: datetime,
        end: datetime,
        tokens: int,
        xp: int,
    ) -> tuple[int, int, bool]:
        """Persist a completed focus session and update user totals.

        Returns (duration_minutes, is_hyperfocus, total_focus_minutes_after).
        """
        duration = end - start
        duration_mins = max(1, int(duration.total_seconds() / 60))
        is_hyperfocus = duration_mins >= HYPERFOCUS_THRESHOLD

        async with aiosqlite.connect(DB_PATH) as db:
            # Insert focus session
            try:
                await db.execute(
                    """
                    ALTER TABLE focus_sessions
                    ADD COLUMN is_hyperfocus BOOLEAN DEFAULT 0
                    """
                )
            except Exception:
                # Column already exists – ignore
                pass

            await db.execute(
                """
                INSERT INTO focus_sessions (
                    discord_id, project_name, start_time, end_time,
                    duration_min, tokens_earned, completed, is_hyperfocus
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    str(user_id),
                    project,
                    start.isoformat(),
                    end.isoformat(),
                    duration_mins,
                    tokens,
                    int(is_hyperfocus),
                ),
            )

            # Update user totals and XP
            await db.execute(
                """
                UPDATE users
                SET broski_tokens = broski_tokens + ?,
                    total_focus_min = COALESCE(total_focus_min, 0) + ?,
                    total_xp = COALESCE(total_xp, 0) + ?
                WHERE discord_id = ?
                """,
                (tokens, duration_mins, xp, str(user_id)),
            )

            # Economy transaction record
            await db.execute(
                """
                INSERT INTO economy_transactions (discord_id, amount, direction, reason)
                VALUES (?, ?, 'earn', ?)
                """,
                (
                    str(user_id),
                    tokens,
                    f"Focus session completed ({duration_mins} min)",
                ),
            )

            # Read back total_focus_min for dashboard
            async with db.execute(
                "SELECT total_focus_min FROM users WHERE discord_id = ?",
                (str(user_id),),
            ) as cursor:
                row = await cursor.fetchone()
                total_focus = row if row and row is not None else duration_mins

            await db.commit()

        return duration_mins, is_hyperfocus, total_focus

    @commands.hybrid_command(name="focus", description="Start a hyperfocus session")
    @app_commands.describe(
        project="What are you working on?",
        minutes="How long do you want to focus? (optional)",
    )
    async def focus_start(
        self,
        ctx: commands.Context,
        *,
        project: str = "Coding",
        minutes: int | None = None,
    ) -> None:
        """Start a focus session for the calling user."""
        user_id = ctx.author.id

        if user_id in self.active_sessions:
            await ctx.send(
                "❌ You already have an active session! Use `/focusend` first.",
            )
            return

        await self._ensure_user_row(user_id, ctx.author.name)

        # Clamp duration if provided
        if minutes is not None:
            minutes = max(5, min(minutes, 180))  # simple guardrail

        self.active_sessions[user_id] = {
            "start": datetime.utcnow(),
            "project": project,
            "duration": minutes,
        }

        # Build response embed
        desc = f"**Project:** {project}"
        if minutes:
            end_time = datetime.utcnow() + timedelta(minutes=minutes)
            desc += f"\n**Planned Duration:** {minutes} minutes (ends at {end_time:%H:%M UTC})"

        embed = discord.Embed(
            title="⏱️ HyperFocus Session Started!",
            description=desc,
            color=0x3498DB,
        )
        embed.add_field(
            name="💰 Rewards",
            value=(
                f"Complete session = **{BASE_REWARD} BROski$** base\n"
                f"+ **{PER_MINUTE_BONUS} BROski$** per minute bonus"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎯 Tips",
            value=(
                "• Close extra tabs\n"
                "• Mute noisy channels\n"
                "• Tiny breaks between sessions"
            ),
            inline=False,
        )
        embed.set_footer(text="You got this, BROski! 🐶♾️")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="focusend", description="End your hyperfocus session")
    async def focus_end(self, ctx: commands.Context) -> None:
        """End the caller's active focus session and award rewards."""
        user_id = ctx.author.id

        if user_id not in self.active_sessions:
            await ctx.send("❌ No active session found! Start one with `/focus`.")
            return

        session = self.active_sessions.pop(user_id)
        start_time: datetime = session["start"]
        project: str = session["project"]

        end_time = datetime.utcnow()
        duration = end_time - start_time
        duration_mins = max(1, int(duration.total_seconds() / 60))

        # Reward calculation
        tokens = BASE_REWARD + duration_mins * PER_MINUTE_BONUS
        xp = duration_mins * XP_PER_MINUTE

        # Apply hyperfocus multiplier if long enough
        if duration_mins >= HYPERFOCUS_THRESHOLD:
            tokens = int(tokens * HYPERFOCUS_MULTIPLIER)

        duration_mins, is_hyperfocus, total_focus = await self._record_session(
            user_id,
            project,
            start_time,
            end_time,
            tokens,
            xp,
        )

        embed = discord.Embed(
            title="🎉 HyperFocus Session Complete!",
            description=f"**Project:** {project}",
            color=0x2ECC71,
        )
        embed.add_field(
            name="⏱️ Duration",
            value=f"**{duration_mins}** minutes",
            inline=True,
        )
        embed.add_field(
            name="💰 Earned",
            value=f"**+{tokens} BROski$**",
            inline=True,
        )
        embed.add_field(
            name="⚡ XP Gained",
            value=f"**+{xp} XP**",
            inline=True,
        )

        if is_hyperfocus:
            embed.add_field(
                name="🏆 Achievement",
                value="**LEGENDARY FOCUS** (hyperfocus session!)",
                inline=False,
            )

        embed.add_field(
            name="📊 Lifetime Focus",
            value=f"Total **{total_focus} minutes** logged.",
            inline=False,
        )
        embed.set_footer(text="Nice work, BROski! 🐶♾️")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="focusstats", description="View your focus stats")
    @app_commands.describe(user="User to inspect (optional)")
    async def focus_stats(
        self,
        ctx: commands.Context,
        user: discord.Member | None = None,
    ) -> None:
        """Show aggregated focus statistics for a user."""
        target = user or ctx.author
        discord_id = str(target.id)

        async with aiosqlite.connect(DB_PATH) as db:
            # Aggregate totals
            async with db.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(duration_min), 0),
                    COALESCE(SUM(CASE WHEN is_hyperfocus = 1 THEN 1 ELSE 0 END), 0)
                FROM focus_sessions
                WHERE discord_id = ? AND completed = 1
                """,
                (discord_id,),
            ) as cursor:
                row = await cursor.fetchone()
                total_sessions = row or 0
                total_minutes = row[^1] or 0
                hyper_count = row[^2] or 0

            # Last 7 days breakdown
            since = (datetime.utcnow() - timedelta(days=7)).isoformat()
            async with db.execute(
                """
                SELECT date(start_time), COALESCE(SUM(duration_min), 0)
                FROM focus_sessions
                WHERE discord_id = ? AND completed = 1 AND start_time >= ?
                GROUP BY date(start_time)
                ORDER BY date(start_time) ASC
                """,
                (discord_id, since),
            ) as cursor:
                rows = await cursor.fetchall()

        # Build a tiny text graph
        day_lines: list[str] = []
        for date_str, minutes in rows:
            # e.g., 2026-03-03 -> Tue
            try:
                day = datetime.fromisoformat(str(date_str)).strftime("%a")
            except Exception:
                day = str(date_str)
            blocks = max(1, minutes // 10)
            bar = "▓" * blocks
            label = f"{day} {bar} {minutes}m"
            if minutes >= HYPERFOCUS_THRESHOLD:
                label += " (🔥)"
            day_lines.append(label)

        graph = "\n".join(day_lines) if day_lines else "No focus sessions logged in the last 7 days."

        # Simple FocusScore approximation
        score = int(5 * (total_minutes ** 0.5) + 10 * hyper_count)

        embed = discord.Embed(
            title=f"📊 Focus Stats – {target.display_name}",
            color=0x1ABC9C,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(
            name="Total Sessions",
            value=str(total_sessions),
            inline=True,
        )
        embed.add_field(
            name="Total Minutes",
            value=str(total_minutes),
            inline=True,
        )
        embed.add_field(
            name="Hyperfocus Sessions",
            value=str(hyper_count),
            inline=True,
        )
        embed.add_field(
            name="FocusScore (PoC)",
            value=str(score),
            inline=True,
        )
        embed.add_field(
            name="Last 7 Days",
            value=f"```\n{graph}\n```",
            inline=False,
        )
        embed.set_footer(text="Keep building that HyperFocus streak, BROski! 🐶♾️")

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Cog setup entrypoint for discord.py extension loading."""
    await bot.add_cog(FocusEngine(bot))
```

## 11. Implementation Roadmap and Timeline (HyperFocus + Architecture)

Here is a practical, phased plan that builds directly on the existing roadmap but emphasizes the HyperFocus feature.

### Phase 0 – Immediate Fixes (0.5–1 day)

- Finish `economy.py` (repair truncated `leaderboard` function and ensure syntactic correctness).
- Create `cogs/` and move `economy.py` and `focus_engine.py` (PoC version) into it.
- Add `.gitignore` and `.dockerignore` and verify `docker-compose up` still works.

### Phase 1 – HyperFocus PoC integration (2–3 days)

- Drop the provided PoC `FocusEngine` into `cogs/focus_engine.py`.
- Ensure `bot.py` loads `cogs.focus_engine` and that `/focus`, `/focusend`, and `/focusstats` work end-to-end.
- Add a few basic tests using pytest + an in-memory SQLite DB to validate reward calculations and stats queries.
- Dogfood in your own Hyperfocus Zone server and iterate on copy/UX.

### Phase 2 – Service/Repository Extraction (1–2 weeks)

- Implement minimal `src/` scaffold and move `bot.py` and cogs under it without behavior changes.
- Introduce `EconomyService` and `FocusService` abstractions backed by `aiosqlite` (not yet PostgreSQL) so cogs call services instead of raw SQL.
- Migrate a subset of tests from `broski_tests.py` to real `tests/` modules targeting services.

### Phase 3 – Infrastructure Hardening (2 weeks)

- Finalize Pydantic `Settings`, structlog logging, Prometheus metrics, and basic Redis-backed rate limiting, using the existing `broski_*` files as reference.
- Move to PostgreSQL in non-production, updating schema to match `broski_models.py`.
- Add GitHub Actions CI (lint + tests + Docker build) and coverage reporting.

### Phase 4 – Advanced HyperFocus and Analytics (2 weeks)

- Implement distraction tracking table/columns and `on_message` listener for nudges.
- Add `/focusconfig` and advanced analytics (period filters, per-project stats, global focus leaderboards).
- Experiment with external dashboard integrations (e.g., small FastAPI service or Grafana view over Prometheus/custom metrics).

This phased plan keeps **quick wins** up front (fixes + PoC HyperFocus), then gradually folds in the more ambitious v4 architecture you have already designed.
