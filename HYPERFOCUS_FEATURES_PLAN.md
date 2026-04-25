# 🧠 HYPERFOCUS FEATURES — Build Plan
> Neurodivergent-first additions to HyperCode V2.4
> Written: April 16, 2026 | **Updated: April 25, 2026**
> **Overall Status: Feature 1 ✅ DONE | Feature 2 ✅ DONE | Features 3–5 PLANNED**

---

## 🗺️ BUILD ORDER (priority stack)

```
1. Micro-Achievement Git Hook    ✅ DONE April 25
2. HyperSplit Agent              ✅ DONE April 25
3. Session Snapshot Agent        ← NEXT — solves "where was I?"
4. Morning Briefing              ← one Discord command, huge daily impact
5. Focus / Panic Mode            ← signature feature, goes viral
```

---

# ✅ FEATURE 1 — Micro-Achievement Git Hook
> **Status: DONE April 25** | Time taken: ~2h

## What it does
- Fires on every `git commit` in V2.4
- Awards BROski$ coins based on commit type
- Sends Discord message via broski-bot

## Real file paths (actual implementation)
```
.git/hooks/post-commit                              ← git hook (chmod +x)
scripts/award-commit-tokens.py                      ← Python logic, calls token API
agents/broski-business-agents/achievement_engine.py ← achievement rules engine
backend/app/routes/achievements.py                  ← API endpoints
```

## API endpoints live
```
GET /api/v1/achievements/history   — last 20 achievements for a user
GET /api/v1/achievements/streak    — current streak count
```

## Achievement rules (live)
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

## Verify it's working
```bash
# Make a commit
git commit --allow-empty -m "fix: test the hook"
# Should see: 🔥 +25 BROski$ — Test fixed!

# Check streak
curl http://localhost:8000/api/v1/achievements/streak
```

---

# ✅ FEATURE 2 — HyperSplit Agent
> **Status: DONE April 25** | Time taken: ~2h

## What it does
- Takes a plain-English task description
- Returns 3–7 microsteps, max 25 mins each
- Ordered: quick win → hard bit → polish
- Each step has a clear "done state"
- Available via API endpoint + Discord `/split` command

## Real file paths (actual implementation)
```
agents/hypersplit/
    main.py          ← FastAPI agent, port 8096
    Dockerfile       ← python:3.11-slim, non-root, security hardened
    requirements.txt ← fastapi, uvicorn, httpx, pydantic, slowapi
    splitter.py      ← core LLM logic (calls Ollama)
    models.py        ← TaskSplitRequest, TaskStep, TaskSplitResponse pydantic models
```

## Env vars
```
OLLAMA_URL=http://hypercode-ollama:11434   (set in docker-compose.agents.yml)
OLLAMA_MODEL=llama3                         (or tinyllama as fallback)
```

## API shape
```
POST /split  (agent direct — port 8096)
POST /api/v1/hypersplit  (proxied through hypercode-core — port 8000)

Request:
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
    }
  ],
  "total_minutes": 45,
  "broski_reward": 75
}
```

## Health + smoke test
```bash
curl http://localhost:8096/health
# → {"status": "healthy", "agent": "hyper-split"}

curl -X POST http://localhost:8000/api/v1/hypersplit \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a Discord summary bot", "max_steps": 5}'
```

---

# 🥉 FEATURE 3 — Session Snapshot Agent
> **Time:** ~2 hours | **Status: PLANNED — next up**

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

# 🎯 FEATURE 4 — Morning Briefing
> **Time:** ~1.5 hours | **Status: PLANNED**

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

# 🚨 FEATURE 5 — Focus / Panic Mode
> **Time:** ~1 hour | **Status: PLANNED**

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
```

---

## 📋 QUICK REFERENCE — Status at a glance

| Feature | Est. Time | Status |
|---|---|---|
| Micro-Achievement Git Hook | 2h | ✅ DONE April 25 |
| HyperSplit Agent | 2h | ✅ DONE April 25 |
| Session Snapshot Agent | 2h | 🔲 Next up |
| Morning Briefing | 1.5h | 🔲 Planned |
| Focus / Panic Mode | 1h | 🔲 Planned |
| **Remaining** | **~4.5h** | |

---

## ✅ DONE CHECKLIST
- [x] Micro-Achievement Git Hook
- [x] HyperSplit Agent
- [ ] Session Snapshot Agent  
- [ ] Morning Briefing `/briefing`
- [ ] Focus / Panic Mode `make focus` / `make calm`
