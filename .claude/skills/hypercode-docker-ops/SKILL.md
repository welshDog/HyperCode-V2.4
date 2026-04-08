---
name: hypercode-docker-ops
description: Manages all Docker and Docker Compose operations for HyperCode services. Use when asked to start, stop, restart, scale, or inspect any HyperCode service, container, or network. Knows the full docker-compose file map and correct start order. Also handles log inspection and container health.
---

# HyperCode Docker Ops

## Service start order (CRITICAL)

```
Tier 1 (INFRA):    redis → postgres
Tier 2 (CORE):     crew-orchestrator → healer → hypercode-core
Tier 3 (AGENTS):   agent-x → all hyper-agents
Tier 4 (UI):       mission-control → broski-terminal → grafana
```

NEVER start Tier 2+ before Tier 1 is healthy.

## Key compose files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full production stack |
| `docker-compose.hyper-agents.yml` | Agent-only services |
| `docker-compose.dev.yml` | Dev with hot reload |
| `docker-compose.nano.yml` | Minimal / low-resource |
| `docker-compose.monitoring.yml` | Grafana + Prometheus |

## Common operations

```bash
# Start full system
./hyperlaunch.sh

# Start single service
docker compose up -d <service-name>

# View logs
docker compose logs -f <service-name>

# Health check all
docker compose ps

# Scale agent
docker compose up -d --scale agent-x=3

# Full restart
docker compose down && ./hyperlaunch.sh
```

## Validation after start

Run: `python scripts/health_check.py --all`
Expected: all services show `healthy` within 60s
