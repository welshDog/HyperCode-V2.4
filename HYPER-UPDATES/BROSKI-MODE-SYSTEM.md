# 🎛️ BROski MODE SYSTEM

**Status:** 🟡 Ready to build  
**Effort:** M (Medium — 2-3 focused sessions)  
**Repo:** HyperCode-V2.4 → `discord-bot/` + `backend/`  
**Created:** 2026-05-31  
**By:** welshDog + Perplexity BROski♾️

---

## 🧠 WHY

Right now BROski is a bot that responds to commands.
The upgrade: BROski becomes a **context-aware operating system** for the whole ecosystem.

You switch MODES depending on what you're doing.
Same Discord. Same BROski. Completely different brain.

> "Like switching gear on a supercar. Same engine. Different behaviour."

---

## 🔵 ALWAYS-ON COMMANDS (Every Mode)

These never change. They exist in ALL modes:

```
/status     → full ecosystem health check (all 42 containers)
/revenue    → Stripe + BROski$ stats today
/deploy     → trigger Vercel deploy
/fix [P0]   → spawn repair agent for named issue
/morning    → DAWN HERALD briefing (HS-013)
/logs       → last 50 lines from Grafana/Loki
/agents     → which agents are alive right now
/mode [name] → switch BROski brain mode
```

---

## 🎮 THE 5 MODES

### 🟢 MODE: `AUTO` — Full Autopilot
> *"Just run the ecosystem bro, don't bother me"*

- Agents self-heal via HEALERS CHORUS (HS-103)
- NIGHT TENDER nightly loop runs automatically (HS-093)
- Morning briefing DM via DAWN HERALD (HS-013)
- Only pings you if something **cannot fix itself**
- All non-critical alerts suppressed

**Skill hooks:** HS-013, HS-093, HS-103, HS-071

---

### 🔴 MODE: `BUILD` — Hyperfocus Dev Mode
> *"I'm coding, give me focused help only"*

Extra commands unlocked:
```
/task       → next task from handover file
/push       → git fetch + commit + push sequence
/check [file] → reads file from GitHub live
/skill [id] → loads a HYPER-SKILLs skill by ID
```

- Suppresses all non-critical alerts
- Silent unless you ask directly
- Pairs with GODFLOW (HS-006) for task routing

**Skill hooks:** HS-006, HS-075, HS-078

---

### 🟡 MODE: `TEACH` — Course Mode
> *"I'm focused on student stuff"*

Extra commands unlocked:
```
/students   → enrollment + engagement stats from Supabase
/stragglers → Catch Stragglers scan, DMs you the list
/module [n] → Module n summary from vault
/broski$    → token economy stats
```

- Alerts only for: payment fails, new enrollments
- Pairs with THE ASCENT (HS-012)

**Skill hooks:** HS-012, HS-026, HS-025

---

### 🟣 MODE: `BOSS` — Big Picture Mode
> *"Show me everything, I'm reviewing the whole empire"*

Extra commands unlocked:
```
/week       → what shipped this week across all repos
/next       → what's next ranked by priority
/empire     → full ecosystem dashboard in one Discord message
```

- Full alerts on
- Revenue + health + agent status + GitHub activity + student count
- Pairs with THE CONDUCTOR (HS-068)

**Skill hooks:** HS-068, HS-070, HS-089

---

### ⚡ MODE: `CHAOS` — Emergency Mode
> *"Something's broken, I need rapid-fire help"*

Extra commands unlocked:
```
/triage     → AI diagnoses the failure, suggests fix
/restart [service] → restart named container
/stream     → real-time container logs in Discord channel
```

- All agents switch to repair priority
- Full alert volume
- Pairs with SOFT LANDING (HS-071) + HEALERS CHORUS (HS-103)

**Skill hooks:** HS-071, HS-103, HS-104

---

## 📋 COMMAND × MODE MATRIX

| Command | AUTO | BUILD | TEACH | BOSS | CHAOS |
|---------|------|-------|-------|------|-------|
| `/status` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/revenue` | 🔕 quiet | 🔕 quiet | ✅ | ✅ | 🔕 |
| `/task` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/students` | ❌ | ❌ | ✅ | ✅ | ❌ |
| `/triage` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/week` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `/empire` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `/morning` | ✅ auto | ✅ | ✅ | ✅ | ❌ |
| `/stream` | ❌ | ❌ | ❌ | ❌ | ✅ |
| Alerts | critical only | silent | enroll+pay | all | all 🔊 |

---

## 🏗️ HOW IT WORKS (Under The Hood)

```
Discord: /mode BUILD
    ↓
BROski bot → POST /api/mode { mode: "BUILD" }
    ↓
FastAPI intent_router.py reads mode from Redis
    ↓
Redis: SET broski:mode:current BUILD
    ↓
All future commands route through mode-aware handler
    ↓
Responds with mode-appropriate behaviour
```

### Redis Key Schema
```
broski:mode:current    → string: AUTO | BUILD | TEACH | BOSS | CHAOS
broski:mode:changed_at → ISO timestamp
broski:mode:changed_by → user Discord ID
```

### FastAPI Intent Router (scaffold)
```python
# backend/routers/broski_mode.py

from fastapi import APIRouter
from redis import Redis
from datetime import datetime

router = APIRouter(prefix="/api/mode", tags=["broski-mode"])
redis = Redis(host="redis", port=6379, decode_responses=True)

VALID_MODES = ["AUTO", "BUILD", "TEACH", "BOSS", "CHAOS"]

@router.post("/")
async def set_mode(mode: str, user_id: str):
    if mode.upper() not in VALID_MODES:
        return {"error": f"Invalid mode. Choose from: {VALID_MODES}"}
    redis.set("broski:mode:current", mode.upper())
    redis.set("broski:mode:changed_at", datetime.utcnow().isoformat())
    redis.set("broski:mode:changed_by", user_id)
    return {"status": "ok", "mode": mode.upper()}

@router.get("/")
async def get_mode():
    mode = redis.get("broski:mode:current") or "AUTO"
    changed_at = redis.get("broski:mode:changed_at")
    return {"mode": mode, "changed_at": changed_at}

def get_current_mode() -> str:
    """Helper for other routers to read current mode."""
    return redis.get("broski:mode:current") or "AUTO"
```

---

## 🚀 BUILD ORDER

1. **Redis mode key** — `broski:mode:current` in existing Redis (already running ✅)
2. **`/api/mode` FastAPI router** — POST to set, GET to read (above scaffold)
3. **`/mode` Discord slash command** — calls FastAPI, confirms back in Discord
4. **Mode-aware intent router** — reads mode before every command dispatch
5. **Wire AUTO mode first** — night loop + self-heal, biggest win
6. **Wire BUILD mode** — `/task`, `/push`, `/check` — you'll use every session
7. **TEACH, BOSS, CHAOS** — add one by one as needed

---

## ✅ DONE WHEN

- [ ] `/mode AUTO` activates autopilot — no ping unless critical
- [ ] `/mode BUILD` shows `/task` and suppresses alerts
- [ ] `/status` works in all 5 modes
- [ ] Mode stored in Redis and survives bot restart
- [ ] `/mode` with wrong name returns helpful error
- [ ] Mode shown in `/morning` briefing DM

---

## 🔗 Related Skills

| Skill | Relevant to |
|-------|------------|
| HS-006 GODFLOW | BUILD mode task routing |
| HS-013 DAWN HERALD | AUTO mode morning briefing |
| HS-068 THE CONDUCTOR | BOSS mode orchestration |
| HS-071 SOFT LANDING | CHAOS mode fallback chain |
| HS-093 NIGHT TENDER | AUTO mode nightly loop |
| HS-103 HEALERS CHORUS | AUTO + CHAOS self-healing |

---

> Built by welshDog — Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁧
> Stop apologising for your brain. Start building. ♾️
