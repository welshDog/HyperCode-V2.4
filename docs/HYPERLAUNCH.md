# 🚀 HyperLaunch — Unified System Initialization Commander

> **One command. Full stack. Zero chaos.**
> HyperLaunch is the single entry point for starting, monitoring, and shutting down the entire HyperCode V2.0 system.

---

## ⚡ The One Command

```bash
# Make executable once
chmod +x hyperlaunch.sh

# Launch everything
./hyperlaunch.sh
```

Or with Python directly:
```bash
python hyperlaunch.py
```

---

## 🎛️ All Commands

| Command | What It Does |
|---------|-------------|
| `./hyperlaunch.sh` | Full system launch |
| `./hyperlaunch.sh --dry-run` | Pre-flight checks only (no containers started) |
| `./hyperlaunch.sh --status` | Live health table for all services |
| `./hyperlaunch.sh --teardown` | Graceful shutdown of all services |
| `./hyperlaunch.sh --watchdog` | Launch + keep guardian watchdog running |
| `./hyperlaunch.sh --tier infra` | Start infrastructure tier only |
| `./hyperlaunch.sh --tier core` | Start core platform tier only |
| `./hyperlaunch.sh --tier agents` | Start AI agents tier only |
| `./hyperlaunch.sh --tier ui` | Start UI/dashboards tier only |
| `./hyperlaunch.sh --skip-preflight` | Skip pre-flight checks (use with care) |

---

## 🏗️ Launch Sequence

HyperLaunch starts services in 4 dependency-ordered tiers:

```
Tier 1: INFRA       ← Must be healthy before anything else starts
  Redis             :6379   State sync + pub/sub backbone
  PostgreSQL        :5432   Persistent agent state + logs

Tier 2: CORE        ← Platform backbone (depends on INFRA)
  Crew Orchestrator :8081   Agent lifecycle manager
  Healer Agent      :8008   Self-healing + auto-recovery
  HyperCode Core    :8000   FastAPI backbone + integrations hub

Tier 3: AGENTS      ← AI agents (depend on CORE)
  Agent X           :8080   Meta-Architect — spawns + evolves agents
  Hyper Architect   :8091   System design agent
  Hyper Observer    :8092   Real-time metrics + alerting
  Hyper Worker      :8093   Background task execution
  DevOps Engineer   :8085   CI/CD + autonomous evolution

Tier 4: UI          ← Dashboards (depend on CORE)
  Mission Control   :8088   Next.js real-time dashboard
  BROski Terminal   :3000   Custom CLI + web UI
  Grafana           :3001   Observability dashboards
```

---

## ✈️ Pre-Flight Checks

Before any container starts, HyperLaunch verifies:

1. **Docker daemon** — is Docker running?
2. **Docker Compose** — is `docker compose` available?
3. **Compose file** — is a `docker-compose.yml` or `docker-compose.hyper-agents.yml` present?
4. **`.env` file** — are secrets loaded?
5. **Required env vars** — `OPENAI_API_KEY`, `REDIS_URL`, `DATABASE_URL`
6. **Disk space** — minimum 2 GB free
7. **Port scan** — checks critical ports 6379, 5432, 8000, 8080, 8081

If any critical check fails, launch is aborted with a clear error message.

---

## 🔗 Real-Time State Synchronization

HyperLaunch publishes system events to Redis `hypercode:system` pub/sub channel:

| Event | When |
|-------|------|
| `system_launching` | Launch sequence begins |
| `tier_infra_complete` | Infra tier healthy |
| `tier_core_complete` | Core tier healthy |
| `tier_agents_complete` | Agents tier healthy |
| `tier_ui_complete` | UI tier healthy |
| `system_live` | All tiers up |
| `launch_failed` | Critical service failure |
| `system_shutdown` | Teardown initiated |
| `watchdog_check` | Guardian health pulse |

All agents subscribed to `hypercode:system` receive these events automatically.

---

## 🛡️ Guardian Watchdog

Run with `--watchdog` to keep a background monitor running after launch:

```bash
./hyperlaunch.sh --watchdog
```

The watchdog:
- Polls all services every 30 seconds
- Publishes `watchdog_check` events to Redis
- Reports unhealthy services in real time
- Runs 10 check cycles (5 minutes) then exits

---

## 🔧 Post-Launch Integration

After all tiers are healthy, HyperLaunch automatically:

1. Triggers **Agent X pipeline scan** — scores all agents and flags any that need evolution
2. Checks **Crew Orchestrator** registration — confirms all agents are registered
3. Writes **system state** to Redis for all modules to read

---

## ⚙️ Requirements

```bash
# Core (required)
pip install fastapi uvicorn httpx

# Optional (pretty output)
pip install rich

# Optional (Redis sync)
pip install redis
```

---

## 🚨 Error Recovery

| Situation | What HyperLaunch Does |
|-----------|----------------------|
| Critical service fails in INFRA tier | Abort immediately, print error |
| Critical service fails in CORE tier | Abort, don't start agents |
| Non-critical service fails (UI) | Log warning, continue |
| Agent X scan fails post-launch | Log warning, system still runs |
| Redis unavailable | Launch continues, sync events skipped |
| `.env` missing | Warn user, continue with environment |

---

## 🎯 Quick Reference Port Map

| Service | Port | URL |
|---------|------|-----|
| Agent X | 8080 | http://localhost:8080 |
| Crew Orchestrator | 8081 | http://localhost:8081 |
| HyperCode Core | 8000 | http://localhost:8000 |
| Healer Agent | 8008 | http://localhost:8008 |
| DevOps Engineer | 8085 | http://localhost:8085 |
| Mission Control | 8088 | http://localhost:8088 |
| Hyper Architect | 8091 | http://localhost:8091 |
| Hyper Observer | 8092 | http://localhost:8092 |
| Hyper Worker | 8093 | http://localhost:8093 |
| BROski Terminal | 3000 | http://localhost:3000 |
| Grafana | 3001 | http://localhost:3001 |
| Redis | 6379 | redis://localhost:6379 |
| PostgreSQL | 5432 | postgresql://localhost:5432 |

---

> 🦅 **Built for HyperCode V2.0 — Designed to be read by Agent X and the entire agent ecosystem.**
> 
> *"One command. Full stack. Zero chaos."*
