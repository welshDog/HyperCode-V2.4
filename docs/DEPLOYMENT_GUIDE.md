# \uD83D\uDE80 HyperCode V2.0 — Deployment Guide

## Quick Start (Local Dev)

```bash
# 1. Clone + env setup
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0
cp .env.example .env
# Edit .env with your keys

# 2. Start core stack
docker compose up -d redis postgres hypercode-core

# 3. Start dashboard
docker compose up -d hypercode-dashboard

# 4. Open Mission Control
open http://localhost:8088
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|------|
| Mission Control | http://localhost:8088 | Main Dashboard |
| Core API | http://localhost:8000/docs | FastAPI Swagger |
| Healer Agent | http://localhost:8008 | Self-Healing |
| Grafana | http://localhost:3001 | Observability |
| Redis | localhost:6379 | Event Bus |

## Docker Compose Variants

| File | Use For |
|------|---------|
| `docker-compose.yml` | Full production stack |
| `docker-compose.nano.yml` | Low-resource dev (8GB RAM) |
| `docker-compose.monitoring.yml` | Grafana + Prometheus only |
| `docker-compose.dev.yml` | Hot-reload development |

## Environment Variables

```bash
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql+asyncpg://user:pass@postgres/hypercode
HYPERCODE_JWT_SECRET=your-secret-here
NEXT_PUBLIC_FF_HYPERFOCUS_MODE=false  # Feature flags
```

## Health Checks

```bash
# Check all services
curl http://localhost:8088/api/health | jq .

# Check healer XP
curl http://localhost:8008/xp/status | jq .

# Check event bus
docker exec $(docker compose ps -q redis) redis-cli LRANGE hypercode:events:all 0 4
```

## Rollback

```bash
# Stop all services
docker compose down --remove-orphans

# Revert to last stable commit
git log --oneline | grep -E '\u2705|STABLE'
git checkout <commit-sha>

# Restart
docker compose up -d
```
