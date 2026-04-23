# START HERE — HyperCode V2.4.2

**Status:** Active  
**Last Updated:** 2026-04-23  
**Applies To:** HyperCode v2.4.2

## Pick a launch path

### Path 1 — Local dev (dev overlays)

```powershell
Copy-Item .env.example .env
docker compose -f .\docker-compose.yml -f .\docker-compose.dev.yml up -d
```

### Path 2 — Core stack only (core API + dashboard + observability)

```powershell
docker compose up -d
```

### Path 3 — Core + specialist agents

```powershell
docker compose --profile agents up -d
```

### Path 4 — Monitoring only (Grafana + Prometheus)

```powershell
docker compose -f .\docker-compose.yml -f .\docker-compose.monitoring.yml up -d
```

### Path 5 — Core + AI backend (optional AI dependencies)

```powershell
docker compose --profile ai up -d
```

## Secrets strategy (local-safe)

- Local dev can use `.env` for convenience.
- For a production-like local run, use Docker secrets:

```powershell
.\scripts\init-secrets.ps1
docker compose -f .\docker-compose.yml -f .\docker-compose.secrets.yml up -d
```

## Verify it’s alive

```powershell
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8002/api/v1/health
curl http://127.0.0.1:8000/api/v1/metrics
curl http://127.0.0.1:8000/api/v1/agents/status
Start-Process http://127.0.0.1:8088
```

## Key ports (local)

| Service | Port | URL |
|---|---:|---|
| Mission Control (dashboard) | 8088 | http://127.0.0.1:8088 |
| HyperCode Core (FastAPI) | 8000 | http://127.0.0.1:8000/api/v1/docs |
| HyperCode AI (FastAPI) | 8002 | http://127.0.0.1:8002/api/v1/docs |
| Crew Orchestrator | 8081 | http://127.0.0.1:8081 |
| Healer Agent | 8008 | http://127.0.0.1:8008 |
| Grafana | 3001 | http://127.0.0.1:3001 |
| Prometheus | 9090 | http://127.0.0.1:9090 |

## Real-time endpoints (Mission Control)

- Uplink: `ws://127.0.0.1:8000/ws/uplink`
- Events: `ws://127.0.0.1:8000/api/v1/ws/events`
- Logs: `ws://127.0.0.1:8000/api/v1/ws/logs`

## Next reads

- Docs hub: [docs/INDEX.md](docs/INDEX.md)
- Quickstart: [docs/QUICKSTART.md](docs/QUICKSTART.md)
- Project rules: [CLAUDE.md](CLAUDE.md)
- Incident playbook: [docs/RUNBOOK.md](docs/RUNBOOK.md)
