# 🧠 HYPERFOCUS FEATURES — Build Plan
> Neurodivergent-first additions to HyperCode V2.4
> Written: April 16, 2026 | Status: Feature 1–2 ✅ DONE (April 25) | Feature 3–5 PLANNED

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

## Status
✅ Implemented in HyperCode V2.4 (April 25, 2026)

## What it does (current implementation)
- Fires on every `git commit` in this repo
- Calls the existing Phase 2 token sync endpoint with an idempotency `source_id=git_<sha>`
- Never blocks commits (fails silently if API is down)

## Implementation (files)
```
scripts/git-hooks/post-commit           ← hook entrypoint (calls the Python script)
scripts/install-git-hooks.ps1           ← installs the hook into .git/hooks/
scripts/pets/git_post_commit.py         ← commit detector + award call
```

## Required env vars
```
COURSE_SYNC_SECRET=<shared secret for /api/v1/economy/award-from-course>
PETS_DISCORD_ID=<discord user id>  (or GIT_DISCORD_ID)
```

## Endpoint used
```
POST /api/v1/economy/award-from-course
```

---

---

# 🥈 FEATURE 2 — HyperSplit Agent
> **Time:** ~3 hours | **Impact:** Removes #1 ADHD friction point before writing a line

## What it does
- Takes a plain-English task description
- Returns 3–7 microtasks, each normalized to 10–25 mins
- Orders them: quick win → hard bit → polish
- Each step has a clear "done state" (curl command, test to run, visual to see)
- Optionally creates GitHub issues for each step
- Available via: Discord `/split`, API endpoint, CLI command

## Status
✅ Implemented in HyperCode V2.4 (April 25, 2026)

## Implementation (files)
```
agents/hyper-split-agent/main.py                         ← agent service (FastAPI), port 8096
agents/hyper-split-agent/Dockerfile                      ← hardened, non-root
agents/hyper-split-agent/requirements.txt
backend/app/api/v1/endpoints/hypersplit.py               ← POST /api/v1/hypersplit (auth)
backend/app/api/api.py                                   ← router wiring
backend/tests/unit/test_hypersplit.py                    ← unit tests (mocked downstream)
docker-compose.yml                                       ← hyper-split-agent service (profile: hyper)
docker-compose.agents.yml                                ← hyper-split-agent service (agents stack)
```

## Service endpoints
```
Agent:   POST http://localhost:8096/split
Backend: POST http://localhost:8000/api/v1/hypersplit
```

## Agent env vars
```
OLLAMA_HOST=http://hypercode-ollama:11434
OLLAMA_MODEL=qwen2.5-coder:3b
```

## Backend env vars (optional override)
```
HYPER_SPLIT_AGENT_URL=http://hyper-split-agent:8096
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
