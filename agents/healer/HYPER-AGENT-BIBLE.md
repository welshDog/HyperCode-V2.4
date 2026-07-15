# 📖 HYPER-AGENT-BIBLE — Healer Agent
> Version 1.0 | HyperCode V2.4 | Read this before touching ANYTHING in this agent.

---

## 🧠 Mission Statement

The Healer Agent is the **immune system of HyperCode V2.4**.

It does ONE thing well: **detect broken containers and bring them back to life**, without making things worse.

> "Do no harm first. Then heal."

The Healer is NOT:
- A deployment tool
- A config manager  
- A scaling system
- A replacement for good container design

---

## ⚡ Core Operating Rules

### Rule 1 — Throttle Contract (Sacred)
Before restarting ANY container, check `throttle:paused:{container}` in Redis.
If that key exists → **DO NOT restart**. The ThrottleAgent or a human has intentionally paused it.

Breaking this rule = you could restart something mid-deploy or mid-debug. Don't.

### Rule 2 — Circuit Breaker Respect
Every container gets its own `CircuitBreaker` instance.
- **CLOSED** → normal, heal freely
- **OPEN** → container is in a known-bad state, **skip healing**, return `circuit_open` status
- **HALF_OPEN** → one test restart allowed, then back to CLOSED if it works

Thresholds: 3 failures → OPEN. 60s recovery timeout → HALF_OPEN test.

Never manually bypass circuit breakers without a strong reason. Reset via `/circuit-breaker/reset/{agent}` if you're sure.

### Rule 3 — Max Restart Budget
Max **3 restarts per container per 5-minute rolling window** (Redis key: `healer:restarts:{name}`).

If a container hits this → it's crash-looping. Healing it again won't help. Let the crash-loop detector fire a Discord alert and let a human investigate.

`force=True` bypass exists for emergencies. Use sparingly.

### Rule 4 — Never Touch Secrets
The Healer reads `HYPERCODE_API_KEY` and `AGENT_API_KEY` from env.
It never logs them, never passes them to other services, never stores them in Redis.

All API key comparisons use `secrets.compare_digest()` — timing-safe. Keep it that way.

### Rule 5 — Fire-and-Forget for XP/Events
Event bus publishes (XP, BROski$ coins, HealEvents) must NEVER crash the healer.
All `event_bus.publish()` calls are wrapped in try/except. Keep it that way.

---

## 🔄 Healing Flow (Step by Step)

```
[Alert arrives via Redis pub/sub OR watchdog OR manual POST /heal]
         ↓
1. Check throttle:paused:{container}  →  paused? STOP, return paused_by_throttle
         ↓
2. Check circuit breaker state        →  OPEN?   STOP, return circuit_open
         ↓
3. Ping agent /health endpoint        →  healthy? STOP, return healthy (no action)
         ↓
4. docker restart {container}
         ↓
5. Wait 2s → ping /health             →  healthy? ✅ return recovered
   Wait 5s → ping /health             →  healthy? ✅ return recovered  
   Wait 10s → ping /health            →  healthy? ✅ return recovered
         ↓
6. All pings failed → raise HealerException → circuit breaker increments failure count
         ↓
7. Publish HealEvent to event bus (fire-and-forget)
8. Increment healer:heals_today in Redis
```

---

## 🚨 Alert Sources

| Source | Channel/Endpoint | Trigger |
|--------|------------------|---------|
| Redis pub/sub | `system_alert` | Any service publishes alert |
| Prometheus/Grafana webhook | `POST /alerts/webhook` | `ServiceDown`, `ContainerKilled`, `ContainerAbsent` |
| Watchdog loop | internal (every 60s) | Smoke test via orchestrator `/execute/smoke` |
| Manual | `POST /heal` | Human or another agent triggers direct heal |
| MAPE-K loop | internal (every 10s) | Autonomous monitoring of DEFAULT_SERVICES |

---

## 🩺 OOM Response Runbook

**Detection:** `OOMKilled: true` OR `ExitCode: 137` in container state.

**What happens automatically:**
1. Discord OOM alert fires (deduplicated — one per container per 10 minutes)
2. Container restart is NOT automatically triggered for OOM (needs human to investigate memory limits first)

**What YOU should do when you see an OOM Discord alert:**
```bash
# 1. Check which container OOM'd
docker inspect {container} | grep -A5 OOMKilled

# 2. Check current memory limit
docker stats {container} --no-stream

# 3. Check docker-compose.agents.yml for deploy.resources.limits.memory
# 4. If limit is too low → raise it in compose + redeploy
# 5. If container genuinely needs that much → investigate the memory leak
```

**Common OOM culprits in this stack:**
- `coder-agent` hitting 1G limit during large file ops → raise to 1.5G
- `ai-backend` during inference → expected, 3G limit is intentional
- `crew-orchestrator` during concurrent task fan-out → check for task queue buildup

---

## 🔁 Crash-Loop Response Runbook

**Detection:** `healer:restarts:{name}` counter ≥ 5 within 5-minute window.

**Discord alert colour:** 🟠 Orange (distinct from OOM red — different root cause).

**What to do:**
```bash
# 1. Read the last 50 log lines
docker logs {container} --tail 50

# 2. Common crash-loop causes:
#    - Missing env var / secret not mounted  → check docker-compose secrets section
#    - Healthcheck command wrong             → check healthcheck test in compose file
#    - Port already in use                  → check for duplicate containers
#    - Dependency not ready                 → check depends_on + condition: service_healthy

# 3. Manual restart after fix:
docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d {container} --force-recreate
```

---

## 📡 When to Alert Discord vs. Stay Quiet

| Event | Discord alert? | Rationale |
|-------|---------------|-----------|
| Single restart, recovers | ❌ No | Normal transient failure |
| OOM kill detected | ✅ Yes | Needs human memory limit review |
| Crash loop (≥5 restarts/5min) | ✅ Yes | Not auto-fixable |
| Circuit breaker OPEN | ❌ No (logged only) | Healer handles retries automatically |
| Agent unresponsive after 3 pings | ❌ No | Circuit breaker handles it |
| Healer itself fails to start | ✅ Yes (health endpoint goes down) | Monitored by compose healthcheck |

---

## 🏗️ File Structure

```
agents/healer/
├── main.py                    ← FastAPI app, circuit breakers, throttle, event bus
├── adapters/
│   ├── docker_adapter.py      ← Docker restart, OOM + crash-loop detection
│   └── discord_notifier.py    ← Discord webhook sender
├── mape_k_engine.py           ← MAPE-K Monitor/Analyse/Plan/Execute loop
├── mape_k_api.py              ← MAPE-K FastAPI routes (/mape-k/*)
├── models.py                  ← HealRequest, HealResult, HealerException, ContainerStatus
├── metrics.py                 ← Prometheus metrics init
├── Dockerfile                 ← Container build
└── HYPER-AGENT-BIBLE.md       ← THIS FILE — read first!
```

---

## 🔑 Key Redis Keys

| Key pattern | TTL | Purpose |
|-------------|-----|---------|
| `healer:restarts:{name}` | 300s (5min) | Rolling restart counter per container |
| `healer:oom_alert:{name}` | 600s (10min) | OOM alert dedup |
| `healer:loop_alert:{name}` | 900s (15min) | Crash-loop alert dedup |
| `healer:heals_today` | Until midnight UTC | Daily heal counter for metrics |
| `agents:heartbeat:healer-01` | 30s | Healer liveness (disappears if healer dies) |
| `throttle:paused:{name}` | Variable | Set by ThrottleAgent — DO NOT restart these |

---

## 🌡️ API Endpoints Quick Reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | ❌ Open | Liveness + readiness |
| GET | `/health/sweep` | ✅ Required | Full container scan |
| POST | `/heal` | ✅ Required | Manual heal trigger |
| POST | `/alerts/webhook` | ❌ Open | Prometheus/Grafana webhook |
| GET | `/circuit-breaker/status` | ✅ Required | All circuit breaker states |
| POST | `/circuit-breaker/reset/{agent}` | ✅ Required | Manual CB reset |
| GET | `/throttle/state` | ✅ Required | Which containers are paused |
| POST | `/throttle/state` | ✅ Required | Pause/unpause containers |
| GET | `/xp/status` | ✅ Required | Healer's XP + BROski$ balance |
| GET | `/mape-k/*` | ✅ Required | MAPE-K loop status + config |

---

## 🎮 BROski$ + XP Economy

The Healer earns rewards for good healing:

| Action | XP | BROski$ |
|--------|----|---------|
| Successful recovery | +50 XP | +10.0 💰 |
| Failed heal attempt | +5 XP | +1.0 💰 |

These are published to the AgentEventBus (Redis streams) as `HealEvent` objects.
The Dashboard reads these for the gamified agent leaderboard.

---

## ✅ Pre-Deploy Checklist

Before deploying changes to the Healer:

- [ ] `HYPERCODE_API_KEY` or `AGENT_API_KEY` env var set in compose
- [ ] `REDIS_URL` points to the correct Redis instance
- [ ] `DOCKER_HOST` / socket proxy configured (`docker-socket-proxy-healer` is up)
- [ ] Discord webhook env var set if you want OOM/loop alerts
- [ ] `HEALER_WATCHDOG_ENABLED=true` only if `HEALER_SMOKE_API_KEY` is also set
- [ ] Healthcheck passes: `curl http://localhost:8002/health`

---

*Built with 💜 by welshDog — Hyperfocus Zone, Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*
*"Heal fast, heal smart, never make it worse."*
