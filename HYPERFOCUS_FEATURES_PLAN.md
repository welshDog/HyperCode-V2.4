# 🧠 HYPERFOCUS FEATURES — Build Plan
> Neurodivergent-first additions to HyperCode V2.4
> Written: April 16, 2026 | **Updated: April 26, 2026**
> **Overall Status: ALL 5 FEATURES ✅ DONE**

---

## 🗺️ BUILD ORDER (priority stack)

```
1. Micro-Achievement Git Hook    ✅ DONE April 25
2. HyperSplit Agent              ✅ DONE April 25
3. Session Snapshot Agent        ✅ DONE April 25
4. Morning Briefing              ✅ DONE April 26
5. Focus / Panic Mode            ✅ DONE April 26
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
scripts/git-hooks/post-commit        ← post-commit hook entrypoint
scripts/install-git-hooks.ps1        ← installs hook into .git/hooks/
scripts/pets/git_post_commit.py      ← awards tokens (idempotent source_id=git_<sha>)
```

## API endpoint used
```
POST /api/v1/economy/award-from-course  (X-Sync-Secret)
```

## Verify it's working
```bash
powershell -File scripts/install-git-hooks.ps1
git commit --allow-empty -m "fix: test the hook"
```

---

# ✅ FEATURE 2 — HyperSplit Agent
> **Status: DONE April 25** | Time taken: ~2h

## What it does
- Takes a plain-English task description
- Returns 3–7 microsteps, max 25 mins each
- Ordered: quick win → hard bit → polish
- Each step has a clear “done state”
- Available via API endpoint + Discord `/split` command

## Real file paths (actual implementation)
```
agents/hyper-split-agent/main.py               ← agent service (FastAPI), port 8096
agents/hyper-split-agent/Dockerfile            ← hardened, non-root
agents/hyper-split-agent/requirements.txt
backend/app/api/v1/endpoints/hypersplit.py     ← POST /api/v1/hypersplit (auth)
backend/tests/unit/test_hypersplit.py          ← unit tests (mocked downstream)
```

## Env vars
```
OLLAMA_HOST=http://hypercode-ollama:11434
OLLAMA_MODEL=qwen2.5-coder:3b
```

## Health + smoke test
```bash
curl http://localhost:8096/health
curl -X POST http://localhost:8000/api/v1/hypersplit \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a Discord summary bot", "max_steps": 5}'
```

---

# ✅ FEATURE 3 — Session Snapshot Agent
> **Status: DONE April 25** | Time taken: ~2h

## What it does
- Watches for git idle >30 mins OR explicit `make snapshot`
- Writes `SESSION.md` in repo root
- On next `make up` / `make start` / `make agents` — SESSION.md displayed automatically

## Real file paths
```
agents/session-snapshot/main.py
agents/session-snapshot/Dockerfile
agents/session-snapshot/snapshot_writer.py
scripts/show-session.sh
Makefile  (snapshot target + auto-show on up/start/agents)
```

## Health + smoke test
```bash
curl http://localhost:8097/health
make snapshot
```

---

# ✅ FEATURE 4 — Morning Briefing `/briefing`
> **Status: DONE April 26** | Time taken: ~1.5h

## What it does
- Discord slash command `/briefing`
- Single clean embed: stack health + BROski$ balance + pulse + next task + last commit
- Green if healthy, orange if issues

## Real file paths
```
agents/broski-bot/src/cogs/briefing.py
agents/broski-bot/src/bot.py      (guild-first sync for instant dev response)
agents/broski-bot/src/settings.py (DISCORD_GUILD_ID wired)
```

## Start
```bash
docker compose --profile discord up -d broski-bot
# → run /briefing in Discord
```

---

# ✅ FEATURE 5 — Focus / Panic Mode
> **Status: DONE April 26** | Time taken: ~1h

## What it does
```
make focus  → stops 14 non-essential containers + starts 25-min countdown
make calm   → restores all containers + awards 75 BROski$ (if session > 10 mins)
```

## Containers stopped in focus mode
```
STOP:  grafana, prometheus, loki, tempo, promtail, cadvisor, node-exporter
       minio, chroma, hypercode-dashboard, hyper-mission-api, hyper-mission-ui
       alertmanager, celery-exporter

KEEP:  hypercode-core, redis, postgres, broski-bot, healer-agent (and all agents)
```

## Real file paths
```
scripts/focus-mode.sh    ← docker stop 14 containers + start 25-min bg timer
scripts/calm-mode.sh     ← docker compose up all stopped + award BROski$
Makefile                 ← focus + calm targets (already present)
.gitignore               ← .focus_session_start already ignored
```

## Quick test
```bash
make focus
# wait a bit...
make calm
# expect: "75 BROski$ awarded!"
```

## Token award logic
- Reads `.focus_session_start` timestamp
- If session > 10 minutes: `POST /api/v1/broski/award` → 75 BROski$
- If core is offline: prints encouragement, no crash
- Reads `DISCORD_USER_ID` from `.env`, falls back to `git config user.email`

---

## 📋 QUICK REFERENCE — Status at a glance

| Feature | Est. Time | Status |
|---|---|---|
| Micro-Achievement Git Hook | 2h | ✅ DONE April 25 |
| HyperSplit Agent | 2h | ✅ DONE April 25 |
| Session Snapshot Agent | 2h | ✅ DONE April 25 |
| Morning Briefing | 1.5h | ✅ DONE April 26 |
| Focus / Panic Mode | 1h | ✅ DONE April 26 |
| **TOTAL** | **~8.5h** | **🏆 ALL DONE** |

---

## ✅ DONE CHECKLIST
- [x] Micro-Achievement Git Hook
- [x] HyperSplit Agent
- [x] Session Snapshot Agent
- [x] Morning Briefing `/briefing`
- [x] Focus / Panic Mode `make focus` / `make calm`

---

> **🎉 ALL 5 HYPERFOCUS FEATURES SHIPPED! 🎉**
> Next up: BROskiPets Phase 0 — see BROSKI_PETS_INTEGRATION_PLAN.md
