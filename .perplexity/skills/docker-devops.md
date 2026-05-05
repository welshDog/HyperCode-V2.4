---
name: docker-devops
description: Use for all Docker, DevOps, container, compose, build, deploy, health, or infrastructure tasks in HyperCode-V2.4. Triggers on: "docker", "container", "compose", "build", "deploy", "health check", "OOM", "make up", "Dockerfile".
---

# 🐳 Docker DevOps Skill

## Key Commands
```bash
# Start full stack
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# AI backend
docker compose --profile ai up -d

# Discord bot
docker compose --profile discord up -d broski-bot

# Focus mode (stops 14 non-essential containers)
make focus

# Calm mode (restores all + awards 75 BROski$)
make calm

# Pre-build check (aborts if <15GB free)
make build
```

## Stack Facts
- 32/32 containers healthy (April 19 2026)
- 5 isolated networks — data-net + obs-net = internal (no internet)
- ALL services have memory limits — never remove them
  - agent-x = 1G | core = 1.5G | postgres = 2G
- OOM exit codes: 137 = OOM killed | 128 = SIGTERM under stress
- Docker context must be 'desktop-linux' on Windows
- healthcheck: use `localhost` not `127.0.0.1` (IPv6 binding)

## Containers Stopped in Focus Mode
STOP: grafana, prometheus, loki, tempo, promtail, cadvisor, node-exporter,
      minio, chroma, hypercode-dashboard, hyper-mission-api, hyper-mission-ui,
      alertmanager, celery-exporter
KEEP: hypercode-core, redis, postgres, broski-bot, healer-agent + all agents

## Key Files
- docker-compose.yml — main stack (65 services)
- docker-compose.secrets.yml — secrets injection (always pair with main)
- docker-compose.spawner.yml — event-driven agent spawner
- docker-compose.mcp-gateway.yml — MCP gateway
- docker-compose.monitoring.yml — observability stack
- Dockerfile.production — hardened, non-root
- scripts/pre-build-check.sh — disk + memory guard

## Redis DB Split
- DB 1 = cache (@cache_response decorator)
- DB 2 = rate limits
- NEVER mix them

## Observability
- Prometheus: monitoring/prometheus/prometheus.yml (NOT root prometheus.yml)
- Grafana: localhost:3001
- Loki + Promtail: log aggregation
- OTLP traces: Tempo via localhost:3001 → Explore → Tempo
