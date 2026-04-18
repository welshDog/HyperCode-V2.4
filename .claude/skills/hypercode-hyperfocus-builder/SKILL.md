---
name: hypercode-hyperfocus-builder
description: Build the 5 ADHD-first Hyperfocus Features for HyperCode V2.4 — Micro-Achievement Git Hook, HyperSplit Agent, Session Snapshot Agent, Morning Briefing, and Focus/Panic Mode. Use when working on any of these 5 features or adding new neurodivergent-first tooling. Full build prompts and patterns inside.
---

# HyperCode Hyperfocus Builder Skill

Full build plans in: `HyperCode-V2.4/HYPERFOCUS_FEATURES_PLAN.md`

## The 5 Features (build in this order)

| # | Feature | Port | Est. | Status |
|---|---------|------|------|--------|
| 1 | Micro-Achievement Git Hook | — | 2h | NOT BUILT |
| 2 | HyperSplit Agent | 8096 | 3h | NOT BUILT |
| 3 | Session Snapshot Agent | 8097 | 2h | NOT BUILT |
| 4 | Morning Briefing `/briefing` | — | 1.5h | NOT BUILT |
| 5 | Focus / Panic Mode | — | 1h | NOT BUILT |

---

## Feature 1 — Micro-Achievement Git Hook

**Files to create:**
```
.git/hooks/post-commit                    ← executable hook
scripts/award-commit-tokens.py            ← awards BROski$
agents/broski-business-agents/achievement_engine.py
backend/app/routes/achievements.py        ← history + streak endpoints
```

**Achievement rules:**
```python
ACHIEVEMENTS = [
    {"id": "first_commit_today",  "tokens": 10,  "msg": "First commit today! 🌅"},
    {"id": "test_fixed",          "tokens": 25,  "msg": "Test fixed! 🟢"},
    {"id": "docstring_written",   "tokens": 5,   "msg": "Docs written! 📝"},
    {"id": "no_critical_cve",     "tokens": 50,  "msg": "Clean security scan! 🔒"},
    {"id": "streak_3_days",       "tokens": 100, "msg": "3-day streak! 🔥"},
    {"id": "streak_7_days",       "tokens": 250, "msg": "7-day streak! 🏆 LEGENDARY"},
]
```

**Critical pattern — never block git:**
```python
try:
    # award tokens
    requests.post(url, json=payload, timeout=2)
except Exception:
    pass  # NEVER raise — never block a commit
```

**API endpoint to call:**
`POST http://localhost:8000/api/v1/broski/award`
Body: `{"discord_id": "...", "amount": 25, "reason": "Test fixed!"}`

---

## Feature 2 — HyperSplit Agent (port 8096)

**Files:**
```
agents/hypersplit/main.py      ← FastAPI, POST /split, GET /health
agents/hypersplit/models.py    ← TaskSplitRequest, TaskStep, TaskSplitResponse
agents/hypersplit/splitter.py  ← Anthropic API call with structured output
agents/hypersplit/Dockerfile   ← MUST match healer-agent Dockerfile exactly
agents/hypersplit/requirements.txt
```

**API shape:**
```python
POST /split
{"task": "Add rate limiting", "context": "FastAPI, Redis available", "max_steps": 5}

Response:
{"steps": [{"order": 1, "title": "...", "done_state": "...", "estimated_minutes": 5, "type": "quick_win"}]}
```

**System prompt for splitter:**
```
You are HyperSplit, a task decomposition agent for neurodivergent developers with ADHD.
Break tasks into steps that are max 25 minutes each.
Each step MUST have a clear done-state (a command to run or a thing to see).
Order: quick win first → hard bit → polish.
Return valid JSON matching the TaskSplitResponse schema.
```

**Add to docker-compose.agents.yml** using existing agent pattern.

---

## Feature 3 — Session Snapshot Agent (port 8097)

**Files:**
```
agents/session-snapshot/snapshot_writer.py  ← git analysis
agents/session-snapshot/main.py            ← FastAPI, POST /snapshot
agents/session-snapshot/Dockerfile
scripts/show-session.sh                    ← display on stack start
SESSION.md                                 ← auto-written, gitignored
```

**SESSION.md format:**
```markdown
# 👋 Welcome Back — Session Snapshot
> Generated: {datetime}

## 📝 Last commit
{last_commit}

## 📁 Changed files (not committed)
{changed_files or "All clean ✅"}

## 🎯 Your next action
{first item from WHATS_DONE.md NEXT UP section}

## 🧪 Last test run
{test_result or "No recent test run found"}
```

**Makefile targets to add:**
```makefile
snapshot:
    @curl -s -X POST http://localhost:8097/snapshot && echo "📸 Snapshot written"

up: show-session
    docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

---

## Feature 4 — Morning Briefing (Discord cog)

**File:** `agents/broski-bot/cogs/briefing.py`

**Discord embed fields:**
```
Title:  "☀️ Morning Briefing — {date}"
Stack:  "✅ All up" or "⚠️ Issues detected"
BROski$: "{balance} coins · Streak: {n} days 🔥"
Next:   "{first NEXT UP item from WHATS_DONE.md}"
Commit: "{last git commit message}"
Footer: rotating motivational line (5 options)
Colour: 0x22c55e (green) if healthy, 0xf59e0b (amber) if issues
```

**Motivational lines (rotate):**
```python
LINES = [
    "Hyperfocus activated. Let's ship. ⚡",
    "Small steps. Big builds. You've got this. 🏴󠁧󠁢󠁷󠁬󠁳󠁠",
    "One task. One win. That's the whole plan. 🎯",
    "Your future users are waiting. Build for them. 🚀",
    "You built 29 containers. Today is just one more step. 🏆",
]
```

**Calls these endpoints:**
- `GET http://hypercode-core:8000/health`
- `GET http://hypercode-core:8000/api/v1/broski/balance/{discord_id}`

---

## Feature 5 — Focus / Panic Mode

**Files:**
```
scripts/focus-mode.sh     ← stops non-essential containers + 25min timer
scripts/calm-mode.sh      ← restores everything + awards 75 BROski$
```

**Containers STOP in focus mode:**
```
grafana prometheus loki tempo promtail cadvisor node-exporter
minio chroma hypercode-dashboard hyper-mission-api hyper-mission-ui alertmanager
```

**Containers STAY UP:**
```
hypercode-core redis postgres broski-bot healer-agent
```

**Makefile targets:**
```makefile
focus:
    @bash scripts/focus-mode.sh

calm:
    @bash scripts/calm-mode.sh
```

**Award on focus completion (> 10 mins):**
```bash
curl -s -X POST http://localhost:8000/api/v1/broski/award \
  -H "Content-Type: application/json" \
  -d "{\"discord_id\": \"$(git config user.email)\", \"amount\": 75, \"reason\": \"Focus session complete 🎯\"}"
```

---

## Shared Patterns for All Features

**Dockerfile (copy healer-agent exactly):**
```dockerfile
FROM python:3.11-slim
RUN apt-get update --allow-releaseinfo-change && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade --no-cache-dir pip setuptools wheel
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
```

**Docker compose entry pattern:**
```yaml
hypersplit:
  build: ./agents/hypersplit
  profiles: [agents]
  networks: [agents-net]
  environment:
    ANTHROPIC_API_KEY_FILE: /run/secrets/anthropic_api_key
  secrets: [anthropic_api_key]
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8096/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Import style (NEVER break this):**
```python
# ✅ CORRECT
from app.services.broski_service import award_tokens

# ❌ WRONG
from backend.app.services.broski_service import award_tokens
```
