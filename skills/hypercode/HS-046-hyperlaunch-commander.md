# HS-046 — HyperLaunch Unified Commander

> **Extracted from:** `hyperlaunch.py` · HyperCode-V2.4
> **What it is:** Single-command, full-system initialisation for the entire HyperCode V2.0 stack

---

## What HyperLaunch Does

1. **Pre-flight checks** — env vars, Docker, ports, disk space
2. **Dependency ordering** — infra first, then core, then agents
3. **Progressive init** — each tier waits for the previous to be healthy
4. **Real-time sync** — Redis pub/sub for cross-module state events
5. **Health monitoring** — continuous polling with retry + backoff
6. **Guardian watchdog** — post-launch background monitor
7. **BROski launch report** — colour-coded summary with port map

## Usage Commands

```bash
python hyperlaunch.py                  # Full launch (interactive)
python hyperlaunch.py --dry-run        # Pre-flight only, no containers
python hyperlaunch.py --tier infra     # Start only infrastructure tier
python hyperlaunch.py --tier core      # Start only core services
python hyperlaunch.py --tier agents    # Start only agent tier
python hyperlaunch.py --status         # Show live system status
python hyperlaunch.py --teardown       # Graceful shutdown
./hyperlaunch.sh                       # One-liner wrapper
```

## Quick Service Links (Post-Launch)

```
🧠 Agent X (Meta-Architect):   http://localhost:8080
🎛️  Crew Orchestrator:         http://localhost:8081
🩺 Healer Agent:              http://localhost:8008
🚀 HyperCode Core:            http://localhost:8000
📊 Mission Control:           http://localhost:8088
💻 BROski Terminal:           http://localhost:3000
📈 Grafana:                   http://localhost:3001
```

## Dependencies

- Python 3.10+
- `rich` (optional, for colour output — graceful fallback if missing)
- Docker + Docker Compose installed and running
- `.env` file populated (copy from `.env.example`)

---

> ⚡ One command = entire stack. Nothing else needed.
