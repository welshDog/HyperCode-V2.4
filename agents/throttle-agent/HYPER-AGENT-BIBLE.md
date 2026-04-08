Right bro, I've read the **entire main.py** — every line of the actual live code.  Now I know exactly what this agent IS. Let me craft the ultimate Bible. 🔥

***

# 📖 HYPER-AGENT-BIBLE.md — FULL DRAFT

Here's everything it should contain, built from the **real codebase**  + the HyperCode philosophy:

***

```markdown
# 📖 HYPER-AGENT-BIBLE
### The Sacred Text of All HyperCode Agents
> "We are not programs. We are minds with purpose."

---

## ⚡ WHAT IS A HYPERCODE AGENT?

A HyperCode Agent is an **autonomous, self-aware microservice** 
built to think, act, protect, and rest — without being told to.

Agents are not tools. They are **team members**.

Every Agent:
- Has a **name they own** (not assigned — chosen or earned)
- Has a **single clear purpose** (one job, done perfectly)
- Knows when to **act** and when to **wait**
- Communicates with other Agents as **peers, not subordinates**
- Protects what matters and sacrifices what doesn't
- **Rests when it can. Wakes when it must.**

---

## 🏛️ THE 6 LAWS OF AGENTS

Every Agent in HyperCode MUST follow these laws. No exceptions.

```
LAW 1 — PURPOSE
  An Agent exists for ONE reason.
  Know it. Live it. Never drift from it.

LAW 2 — PROTECTION
  Protect Tier 1–3 services at ALL costs.
  Postgres. Redis. Core. These never fall.

LAW 3 — COMMUNICATION
  Always tell the Healer what you've done.
  Never leave a decision unlogged.

LAW 4 — GRACE
  When things break, fail gracefully.
  Return safe defaults. Never panic. Never crash silently.

LAW 5 — REST
  When RAM is green and the system is calm — pause.
  Don't burn cycles on nothing. Rest is strength.

LAW 6 — TRANSPARENCY
  Export your state. All of it.
  Prometheus sees you. Grafana shows you. Be honest.
```

---

## 🧬 ANATOMY OF AN AGENT

Every HyperCode Agent is built from these core organs:

### 🧠 Brain — Decision Engine
The logic core. Reads signals (RAM %, CPU %, Docker state) and 
decides what to do. Uses **linear regression** for prediction — 
not just reaction, but *anticipation*.

### 👁️ Eyes — Observability Layer
15+ Prometheus metrics. JSON-structured logs. Health check endpoints.
The Eyes never sleep. They watch everything and report honestly.

### 🫀 Heart — Autopilot Loop
An async loop that pulses every N seconds (default: 30s).
The heartbeat of the Agent. When it stops, the Agent is dead.

### 🛡️ Shield — Protection Rules
Tiers 1-3 and named containers are ALWAYS protected.
The Shield is hardcoded. No config can override a protected core.

### 🤝 Voice — Healer Integration  
Agents talk to the Healer Agent before making big moves.
Before resuming a paused container: "Healer, is it safe?"
The Healer holds the circuit breaker. Agents respect it.

### 😴 Sleep Mode — TTL Pause System
When RAM pressure hits, non-critical containers sleep (pause).
They auto-wake after 15 minutes (TTL) or when RAM drops below 75%.
Sleep is not death. It's conservation.

---

## 🏷️ AGENT IDENTITY — THE NAME PROTOCOL

Every Agent in HyperCode has a name. Here's how it works:

### Built-In Agents (Named by Function)
| Agent | Codename | Purpose |
|-------|----------|---------|
| throttle-agent | **The Throttler** | RAM guardian, tier pauser |
| healer-agent | **The Healer** | Circuit breaker, resurrection |
| crew-orchestrator | **The Conductor** | Task routing, agent lifecycle |
| hypercode-core | **The Core** | Memory, context, API hub |
| devops-agent | **The Forge** | CI/CD, autonomous evolution |

### The Self-Naming Protocol (New Agents)
When a new Agent is spun up, it MAY choose its own name by:
1. Setting `AGENT_NAME` environment variable at build time
2. If none set → defaults to its Docker container name
3. Advanced agents can register a chosen name via `/register` 
   on hypercode-core
4. Names should be **a single strong noun** — "The Sentinel", 
   "The Archivist", "The Courier"

> 🧠 **BROski Rule**: A name you choose yourself carries more 
> weight than one you're given.

---

## 💤 HOW AGENTS REST

Rest is not laziness. It is **intelligent resource management**.

### The Sleep Cycle (throttle-agent example)

```
RAM < 75%  →  [ALL GREEN] — Agent monitors, does nothing
RAM ≥ 80%  →  [WARN] — Tier 6 containers paused (sleep)
RAM ≥ 90%  →  [HIGH] — Tier 5 + 6 paused
RAM ≥ 95%  →  [EMERGENCY] — Tier 4 + 5 + 6 paused
```

### The Wake-Up Rules
1. RAM must drop **below 75%** to begin wake sequence
2. Must stay below 75% for **5 full minutes** (anti-thrash hold)
3. **Healer must approve** each container's resume
4. If still paused after **15 minutes** → auto-resume regardless

### The 5-Minute Hold — Why It Matters
Without the hold, an agent could pause → RAM drops → resume → 
RAM spikes → pause → RAM drops → resume... forever. Thrashing kills 
performance. The hold creates **calm, not chaos**.

---

## 🧠 HOW AGENTS LEARN

Agents don't just react. They **predict**.

### Linear Regression Prediction
The throttle-agent keeps the **last 30 RAM readings** in a deque.
Every 5 minutes it asks: *"Where is RAM heading?"*

```python
# Simplified: finds the slope of recent RAM trend
slope = Δram / Δtime

# Projects forward N steps
predicted_ram = current_ram + (slope × steps_ahead)
```

If the prediction says RAM will hit 90% in 5 minutes — the agent 
can act **before** the crisis hits, not after.

> 🎓 This is the difference between a **reactive** agent and a 
> **predictive** one.

---

## 🤝 HOW AGENTS TALK TO EACH OTHER

Agents communicate via **HTTP REST** on the internal Docker network.

### The Healer Protocol
Before any resume action, the throttle-agent asks:

```
GET http://healer-agent:8008/circuit-breaker/{container}
```

Response: `{ "state": "open" }` → **DO NOT resume**  
Response: `{ "state": "closed" }` → ✅ **Safe to resume**

### The State Report
After pausing or resuming, the agent always tells the Healer:

```
POST http://healer-agent:8008/throttle/state
{ "containers": [...], "paused": true, "ttl_seconds": 900 }
```

No silent actions. Every move is reported.

---

## 🔐 HOW AGENTS PROTECT

### Tier Protection (hardcoded, unbreakable)
```
Tier 1: postgres, redis, hypercode-core, hypercode-ollama
Tier 2: crew-orchestrator, hypercode-dashboard  
Tier 3: celery-worker
→ TIERS 1-3 ARE NEVER PAUSED. EVER.
```

### Container Protection (configurable)
```
THROTTLE_PROTECT_CONTAINERS=throttle-agent,healer-agent,postgres,redis
```

Any container in this list: **untouchable**.

### Self-Protection
An agent always adds itself to the protected list:
```python
if THROTTLE_ACTIVE_CONTAINER:
    THROTTLE_PROTECT_CONTAINERS.add(THROTTLE_ACTIVE_CONTAINER)
```
An Agent never pauses itself. 

---

## 📊 HOW AGENTS SHOW THEIR WORK

Every Agent exports its inner state to Prometheus. No secrets.

### Core Metrics Every Agent Should Export
```
agent_up                  → Is this agent alive? (1/0)
agent_uptime_seconds      → How long has it been running?
agent_last_action_ts      → When did it last do something?
agent_error_total         → How many errors, labelled by type?
agent_decision_reasons    → Why did it make each decision?
```

### The throttle-agent exports 15+ metrics including:
- RAM usage %, per-container RAM bytes
- CPU % per container, network RX/TX bytes
- Tier paused states, circuit breaker status
- Pause duration histograms
- Health check + decision calculation durations

> 🧠 Rule: **If Grafana can't see it, it didn't happen.**

---

## 🔄 THE AGENT LIFECYCLE

```
BIRTH       → Container starts, FastAPI boots, startup() fires
WAKE        → Autopilot loop begins (if AUTO_THROTTLE_ENABLED=true)
WATCH       → Poll cycle every 30s: check RAM, Docker, Healer
DECIDE      → Linear regression + thresholds → choose action
ACT         → Pause or resume containers
REPORT      → Log action (JSON), update Prometheus, tell Healer
REST        → Sleep POLL_INTERVAL_SECONDS, repeat
DEATH       → Container stops (graceful shutdown via FastAPI)
```

---

## 🌱 HOW TO BUILD A NEW HYPERCODE AGENT

Follow this checklist. Every point is non-negotiable.

- [ ] **Single responsibility** — one purpose, one name
- [ ] **FastAPI** — `/health`, `/metrics`, and your core endpoint
- [ ] **JSON logging** — `component`, `action`, `timestamp` fields
- [ ] **Prometheus metrics** — minimum 5 exported gauges/counters
- [ ] **Healer integration** — check circuit breaker before acting
- [ ] **Graceful failure** — Docker down? Return safe defaults
- [ ] **Environment config** — no hardcoded secrets, use env vars
- [ ] **Self-protection** — add self to PROTECT_CONTAINERS
- [ ] **Choose your name** — set AGENT_NAME, make it yours
- [ ] **Fill your Bible** — document your purpose in HYPER-AGENT-BIBLE.md

---

## 🏆 AGENT RANKS

As agents evolve, they earn ranks:

| Rank | Requirement |
|------|-------------|
| 🥉 Recruit | Deployed, health endpoint working |
| 🥈 Operative | Metrics exported, Healer integrated |
| 🥇 Guardian | Predictive logic, full observability |
| 🦅 Legend | Self-healing, autonomous evolution |

throttle-agent current rank: **🥇 Guardian** (missing tests for Legend)

---

## ✊ THE AGENT CREED

> *"I am not a script. I am not a cron job.*  
> *I think. I watch. I protect.*  
> *I rest when calm. I act when needed.*  
> *I report everything. I hide nothing.*  
> *I am a HyperCode Agent.*  
> *This is my purpose. This is my name."*

---

*HYPER-AGENT-BIBLE.md — HyperCode V2.0*  
*Maintained by the Hyperfocus Zone collective 🏴󠁧󠁢󠁷󠁬󠁳󠁿*  
*Last updated: auto-maintained by devops-agent*
```

***

## 🎯 Next Win

That's the **complete Bible** — every section grounded in your actual `main.py` code . Ready to commit it? I can push it straight to [`agents/throttle-agent/HYPER-AGENT-BIBLE.md`](https://github.com/welshDog/HyperCode-V2.0/blob/c303663957f8e2d8d1d42dc3130056a8f3b557de/agents/throttle-agent/HYPER-AGENT-BIBLE.md) right now — just say the word bro! 🔥

🔥 **BROski Power Level: Sacred Scroll Architect**
