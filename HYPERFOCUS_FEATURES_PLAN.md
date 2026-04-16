# 🧠 HYPERFOCUS FEATURES — Build Plan
> Neurodivergent-first additions to HyperCode V2.4
> Written: April 16, 2026 | Status: PLANNED — ready to build

---

## 🗺️ BUILD ORDER (priority stack)

```
1. Micro-Achievement Git Hook    ← 50 lines, immediate dopamine loop
2. HyperSplit Agent              ← #1 ADHD friction point
3. Session Snapshot Agent        ← solves "where was I?" personally
4. Morning Briefing              ← one Discord command, huge daily impact
5. Focus / Panic Mode            ← signature feature, goes viral
```

---

---

# 🥇 FEATURE 1 — Micro-Achievement Git Hook
> **Time:** ~2 hours | **Impact:** Every single commit feels rewarding

## What it does
- Fires on every `git commit` in V2.4 (and optionally SDK + Course repos)
- POSTs to existing BROski$ token service
- Awards coins for: first commit of day, fixing a test, writing a docstring, streaks
- Sends a one-line Discord message via broski-bot: "🔥 +25 BROski$ — test fixed!"

## Files to create / edit
```
.git/hooks/post-commit                    ← git hook script
scripts/award-commit-tokens.py            ← Python logic, calls token API
agents/broski-business-agents/achievement_engine.py  ← achievement rules
backend/app/routes/achievements.py        ← new API endpoint (if not exists)
```

## Achievement rules
```python
ACHIEVEMENTS = [
    {"id": "first_commit_today",   "tokens": 10,  "msg": "First commit today! 🌅"},
    {"id": "test_fixed",           "tokens": 25,  "msg": "Test fixed! 🟢"},
    {"id": "docstring_written",    "tokens": 5,   "msg": "Docs written! 📝"},
    {"id": "no_critical_cve",      "tokens": 50,  "msg": "Clean security scan! 🔒"},
    {"id": "streak_3_days",        "tokens": 100, "msg": "3-day streak! 🔥"},
    {"id": "streak_7_days",        "tokens": 250, "msg": "7-day streak! 🏆 LEGENDARY"},
]
```

## Terminal prompt — paste this to build it

```
You are building the Micro-Achievement Git Hook for HyperCode V2.4.
Repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- from app.X import Y — never from backend.app.X
- 4 spaces Python indent
- Stripe webhook always rate-limit exempt — don't touch it
- Conventional commits: feat: fix: docs: chore:

Read these files first:
1. backend/app/services/broski_service.py — find award_tokens() function signature
2. backend/app/core/config.py — get API URL + token settings
3. agents/broski-business-agents/ — see what's already there
4. .git/hooks/ — check what hooks exist

Then build:

1. scripts/award-commit-tokens.py
   - Reads git log --oneline -1 to get commit message
   - Detects achievement type from message (fix: = test_fixed candidate, docs: = docstring candidate)
   - Checks Redis key "achievements:last_commit_date:{user}" to detect first-commit-today
   - Checks Redis key "achievements:streak:{user}" for streak count
   - POSTs to http://localhost:8000/api/v1/broski/award with {"discord_id": from .env or git config, "amount": tokens, "reason": achievement_msg}
   - Prints coloured output: "🔥 +25 BROski$ — Test fixed!"
   - Gracefully fails silently if API is down (never block a commit)

2. .git/hooks/post-commit (executable script)
   - Calls: python scripts/award-commit-tokens.py
   - Must be chmod +x
   - Fails silently — never block git operations

3. backend/app/routes/achievements.py
   - GET /api/v1/achievements/history — returns last 20 achievements for a user
   - GET /api/v1/achievements/streak — returns current streak count
   - Use existing broski DB patterns

4. Wire achievements router into backend/app/api/api.py

5. Write tests/test_achievements.py with at least 3 test cases

After writing all files, verify the hook is executable:
ls -la .git/hooks/post-commit
```

---

---

# 🥈 FEATURE 2 — HyperSplit Agent
> **Time:** ~3 hours | **Impact:** Removes #1 ADHD friction point before writing a line

## What it does
- Takes a plain-English task description
- Returns 3–5 steps, max 25 mins each
- Orders them: quick win → hard bit → polish
- Each step has a clear "done state" (curl command, test to run, visual to see)
- Optionally creates GitHub issues for each step
- Available via: Discord `/split`, API endpoint, CLI command

## Files to create
```
agents/hypersplit/
    main.py              ← FastAPI agent, port 8096
    Dockerfile           ← python:3.11-slim + security hardening
    requirements.txt
    splitter.py          ← core LLM logic
    models.py            ← Task, Step pydantic models
```

## API shape
```python
POST /split
{
  "task": "Add rate limiting to the agent endpoints",
  "context": "FastAPI, Redis already available, slowapi installed",
  "max_steps": 5,
  "step_duration_minutes": 25
}

Response:
{
  "task": "Add rate limiting...",
  "steps": [
    {
      "order": 1,
      "title": "Verify slowapi is importable",
      "description": "Run: python -c 'import slowapi; print(slowapi.__version__)'",
      "done_state": "See version printed, no ImportError",
      "estimated_minutes": 5,
      "type": "quick_win"
    },
    ...
  ],
  "total_minutes": 45,
  "broski_reward": 75
}
```

## Terminal prompt — paste this to build it

```
You are building the HyperSplit Agent for HyperCode V2.4.
Repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- from app.X import Y — never from backend.app.X
- python:3.11-slim base image
- 4 spaces Python indent
- Port convention: check agents/ for used ports, use next available around 8096
- Security hardening: non-root user, apt-get upgrade, pip upgrade in Dockerfile
- Conventional commits: feat: fix: docs: chore:

Read these files first:
1. agents/healer-agent/main.py — use as pattern for agent FastAPI structure
2. agents/healer-agent/Dockerfile — use as Dockerfile pattern exactly
3. backend/app/core/config.py — get ANTHROPIC_API_KEY / OPENAI_API_KEY setting names
4. docker-compose.agents.yml — see how agents are registered
5. agents/ directory listing — find an unused port around 8096

Then build:

1. agents/hypersplit/models.py
   - TaskSplitRequest: task (str), context (str default ""), max_steps (int default 5), step_duration_minutes (int default 25)
   - TaskStep: order, title, description, done_state, estimated_minutes, type (quick_win/hard/polish)
   - TaskSplitResponse: task, steps list, total_minutes, broski_reward (int, 15 per step)

2. agents/hypersplit/splitter.py
   - Uses Anthropic Claude API (anthropic library) — check what's in existing agent requirements
   - System prompt: "You are HyperSplit, a task decomposition agent for neurodivergent developers with ADHD. Break tasks into steps that are max 25 minutes, have a clear done state, and are ordered with a quick win first."
   - Returns structured JSON matching TaskSplitResponse
   - Include fallback if API fails: return 3 generic steps with the task split naively

3. agents/hypersplit/main.py
   - FastAPI app on correct port
   - POST /split — calls splitter, returns TaskSplitResponse
   - GET /health — standard health check matching other agents pattern
   - Rate limit: 10/minute on /split (uses slowapi pattern from main hypercode-core)

4. agents/hypersplit/Dockerfile
   - Match healer-agent Dockerfile EXACTLY for security hardening
   - python:3.11-slim, non-root user, apt-get upgrade, pip upgrade

5. agents/hypersplit/requirements.txt
   - fastapi, uvicorn, anthropic, pydantic, slowapi — pin versions matching other agents

6. Add hypersplit to docker-compose.agents.yml following existing agent pattern
   - profile: agents
   - network: agents-net
   - env: ANTHROPIC_API_KEY from secrets

7. Wire /split command into broski-bot Discord:
   - Read agents/broski-bot/ structure first
   - Add /split slash command that calls http://hypersplit:8096/split
   - Returns a Discord embed with each step as a field
   - Each step numbered with emoji: 1️⃣ 2️⃣ 3️⃣

After writing: verify Dockerfile syntax and that all imports resolve.
```

---

---

# 🥉 FEATURE 3 — Session Snapshot Agent
> **Time:** ~2 hours | **Impact:** Solves "where was I?" — personal game-changer

## What it does
- Watches for git idle >30 mins OR explicit `make snapshot`
- Writes `SESSION.md` in repo root with:
  - Files changed since last commit
  - Last commit message
  - Any failing tests (from last pytest run)
  - Single suggested next action
- On next `make up` or `make start` — SESSION.md displayed in terminal automatically

## Files to create
```
agents/session-snapshot/
    main.py
    Dockerfile
    requirements.txt
    snapshot_writer.py   ← git analysis logic
SESSION.md               ← auto-written, gitignored
scripts/show-session.sh  ← displays SESSION.md on stack start
```

## Terminal prompt — paste this to build it

```
You are building the Session Snapshot Agent for HyperCode V2.4.
Repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- from app.X import Y — never from backend.app.X
- python:3.11-slim base image
- 4 spaces Python indent
- Conventional commits: feat: fix: docs: chore:

Read these first:
1. agents/healer-agent/main.py — agent pattern
2. agents/healer-agent/Dockerfile — security hardening pattern
3. Makefile — see how to add make targets, current start command
4. .gitignore — check if SESSION.md is already ignored

Then build:

1. agents/session-snapshot/snapshot_writer.py
   Functions:
   - get_changed_files() → runs "git status --short", returns list of changed files
   - get_last_commit() → runs "git log --oneline -1", returns string
   - get_last_test_result() → reads coverage.xml or pytest last output if exists
   - get_suggested_next_action() → reads WHATS_DONE.md "NEXT UP" section, returns first item
   - write_session_md(path) → writes SESSION.md with all above data
   
   SESSION.md format (short, scannable):
   ```
   # 👋 Welcome Back — Session Snapshot
   > Generated: {datetime}
   
   ## 📝 Last commit
   {last_commit}
   
   ## 📁 Changed files (not committed)
   {changed_files or "All clean ✅"}
   
   ## 🎯 Your next action
   {suggested_next_action}
   
   ## 🧪 Last test run
   {test_result or "No recent test run found"}
   ```

2. agents/session-snapshot/main.py
   - FastAPI on port 8097
   - POST /snapshot — triggers snapshot_writer.write_session_md()
   - GET /health — standard check
   - Background task: poll git status every 5 minutes, auto-write if idle detected

3. agents/session-snapshot/Dockerfile — match healer exactly

4. scripts/show-session.sh
   - Checks if SESSION.md exists
   - If yes: cat it with a banner "━━━ LAST SESSION ━━━"
   - If no: echo "Fresh session — check WHATS_DONE.md"

5. Add to Makefile:
   - "snapshot" target: curl -X POST http://localhost:8097/snapshot
   - Edit "up" / "start" targets to call show-session.sh after stack starts

6. Add SESSION.md to .gitignore (it's personal context, never commit)

7. Add session-snapshot to docker-compose.agents.yml
```

---

---

# 🎯 FEATURE 4 — Morning Briefing
> **Time:** ~1.5 hours | **Impact:** Perfect launchpad for every dev day

## What it does
- Discord slash command `/briefing`
- Returns max 8 lines:
  - Stack status (all containers up? Y/N)
  - BROski$ balance + today's streak
  - 1 recommended task from NEXT UP in WHATS_DONE.md
  - Last commit (when was it?)
  - One motivational line

## Files to edit / create
```
agents/broski-bot/cogs/briefing.py    ← new Discord cog
```

## Terminal prompt — paste this to build it

```
You are adding the /briefing slash command to the BROski Discord bot in HyperCode V2.4.
Repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- from app.X import Y — never from backend.app.X
- 4 spaces Python indent
- Conventional commits: feat: fix: docs: chore:

Read these first:
1. agents/broski-bot/ — full directory listing
2. agents/broski-bot/main.py or bot.py — how the bot is structured, how cogs are loaded
3. agents/broski-bot/cogs/ — read ONE existing cog to understand the pattern
4. backend/app/routes/ — find the health + broski token endpoints to call

Then build agents/broski-bot/cogs/briefing.py:

The cog must:
1. Register a /briefing slash command
2. Call http://hypercode-core:8000/health — check status
3. Call http://hypercode-core:8000/api/v1/broski/balance/{discord_id} — get token balance
4. Read WHATS_DONE.md "NEXT UP" section — first item only
5. Call git log --oneline -1 for last commit (or hit an API endpoint if available)
6. Build a Discord Embed (not plain text) with:
   - Title: "☀️ Morning Briefing — {date}"
   - Field: "Stack" → "✅ All up" or "⚠️ Issues detected"
   - Field: "BROski$" → "{balance} coins"
   - Field: "Next Task" → "{first NEXT UP item}"
   - Field: "Last Commit" → "{commit message}"
   - Footer: one of 5 rotating motivational lines (ADHD-friendly, short, punchy)
7. Colour: green if stack healthy, orange if issues

Then wire the cog into the bot's cog loading — read how existing cogs are loaded and follow same pattern exactly.

Motivational lines to rotate:
- "Hyperfocus activated. Let's ship. ⚡"
- "Small steps. Big builds. You've got this. 🏴󠁧󠁢󠁷󠁬󠁳󠁿"
- "One task. One win. That's the whole plan. 🎯"
- "Your future users are waiting. Build for them. 🚀"
- "You built 29 containers. Today is just one more step. 🏆"
```

---

---

# 🚨 FEATURE 5 — Focus / Panic Mode
> **Time:** ~1 hour | **Impact:** Signature feature. The one that goes viral.

## What it does
```
make focus  → stops non-essential containers + opens current task + 25min timer
make calm   → spins everything back up + awards tokens for completing a focus session
```

## Containers stopped in focus mode
```
STOP:  grafana, prometheus, loki, tempo, promtail, cadvisor, node-exporter
       minio, chroma, dashboard, hyper-mission-api, hyper-mission-ui
KEEP:  hypercode-core, redis, postgres, broski-bot, healer-agent
```

## Terminal prompt — paste this to build it

```
You are adding Focus Mode and Calm Mode to HyperCode V2.4.
Repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- Conventional commits: feat: fix: docs: chore:
- Stripe webhook always exempt — don't touch docker-compose.yml networking

Read these first:
1. Makefile — full file, understand current targets and style
2. docker-compose.yml — get the exact service names for observability stack
3. scripts/ — see what scripts already exist

Then build:

1. scripts/focus-mode.sh
   - Stops these containers (docker stop, not docker compose down):
     grafana, prometheus, loki, tempo, promtail, cadvisor, node-exporter,
     minio, chroma, hypercode-dashboard, hyper-mission-api, hyper-mission-ui,
     alertmanager, celery-exporter
   - Prints: "🎯 FOCUS MODE — {N} containers stopped. Core stack running."
   - Prints: "⏱️  25 minute timer started. GO."
   - Starts a 25-minute countdown using: (sleep 1500 && echo "⏰ 25 mins up! Run 'make calm' to restore." && notify-send "HyperCode" "Focus session complete! 🏆" 2>/dev/null || true) &
   - Writes .focus_session_start timestamp file

2. scripts/calm-mode.sh  
   - Starts all stopped containers back up:
     docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d {service names}
   - Reads .focus_session_start, calculates duration
   - If duration > 10 minutes: POSTs to http://localhost:8000/api/v1/broski/award
     {"discord_id": from git config user.email or .env, "amount": 75, "reason": "Focus session complete 🎯"}
   - Prints: "🌊 CALM MODE — Everything back up. You earned 75 BROski$! 🏆"
   - Deletes .focus_session_start

3. Add to Makefile:
   focus:
       @bash scripts/focus-mode.sh
   
   calm:
       @bash scripts/calm-mode.sh
   
   Add to .gitignore: .focus_session_start

4. Update WHATS_DONE.md NEXT UP section — move Focus Mode from planned to in-progress

After writing: verify scripts are valid bash with bash -n scripts/focus-mode.sh
```

---

---

## 📋 QUICK REFERENCE — All 5 prompts at a glance

| Feature | Est. Time | Prompt Section |
|---|---|---|
| Micro-Achievement Git Hook | 2h | Feature 1 |
| HyperSplit Agent | 3h | Feature 2 |
| Session Snapshot Agent | 2h | Feature 3 |
| Morning Briefing | 1.5h | Feature 4 |
| Focus / Panic Mode | 1h | Feature 5 |
| **Total** | **~9.5h** | |

---

## 🚀 HOW TO BUILD WITH CLAUDE

**Option A — One at a time (recommended for review):**
Copy the terminal prompt from any Feature section above. Say to Claude:
> "Build Feature X — here's the prompt: [paste]"

**Option B — Parallel (fastest):**
Say: "go parallel features 1 and 2" — Claude spawns 2 agents simultaneously.

**Option C — All 5 parallel:**
Say: "go parallel all 5" — Claude spawns all 5 agents at once. ~30 mins wall clock.

---

## ✅ DONE (when built)
- [ ] Micro-Achievement Git Hook
- [ ] HyperSplit Agent
- [ ] Session Snapshot Agent  
- [ ] Morning Briefing `/briefing`
- [ ] Focus / Panic Mode `make focus` / `make calm`
