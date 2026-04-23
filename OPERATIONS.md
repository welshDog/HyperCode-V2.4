# HyperCode Docker Operations Guide

## Overview

This guide covers operational tasks for running a 40+ container HyperCode deployment in production. All critical recommendations from the system health audit have been automated via scripts in `scripts/`.

---

## Quick Start

### Pre-Flight Checks

```bash
# Validate compose config
docker compose config --quiet

# Run full health check
bash scripts/health-check.sh

# View container status
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Health}}"
```

### Daily Operations

```bash
# Backup critical volumes
bash scripts/backup-volumes.sh

# Monitor resource usage in real-time
docker stats

# Check Prometheus metrics
curl http://localhost:9090/api/v1/targets

# View AlertManager alerts
curl http://localhost:9093/api/v1/alerts
```

---

## Critical Components

### Core Services (Always Running)

| Service | Port | Purpose | Criticality |
|---------|------|---------|------------|
| hypercode-core | 8000 | Main API & agent orchestrator | CRITICAL |
| PostgreSQL | 5432 | Primary database | CRITICAL |
| Redis | 6379 | Cache & session store | CRITICAL |
| Prometheus | 9090 | Metrics collection | HIGH |
| Grafana | 3001 | Dashboards & visualization | HIGH |

### Agent Services (Profile-Gated)

Agents are enabled via profiles:

```bash
# Enable all agents
docker compose --profile agents up -d

# Enable specific profile
docker compose --profile hyper up -d

# Disable agents (stop but keep volumes)
docker compose --profile agents down
```

### Infrastructure Services

| Service | Purpose | Auto-Restart |
|---------|---------|--------------|
| docker-socket-proxy (×3) | Safe Docker API access | Yes |
| healer-agent | Fault detection & recovery | Yes (always) |
| cadvisor | Container metrics | Yes |
| node-exporter | System metrics | Yes |

---

## Health Monitoring

### Prometheus Alerts

Critical alerts are configured in `monitoring/prometheus/hypercode-alerts.yml`:

- **Container Crashed** — fires if uptime resets
- **HighMemoryUsage** — triggers at 90% of limit
- **HighCPUUsage** — warns at 80%+ sustained
- **CoreServiceFailed** — immediate escalation for hypercode-core, PostgreSQL, Redis
- **AgentHealthCheckFailing** — agent probe missed 3+ times
- **CeleryQueueBacklog** — async task queue exceeding capacity

### Viewing Alerts

```bash
# Web UI
http://localhost:9093  # AlertManager

# CLI
curl http://localhost:9093/api/v1/alerts | jq '.data[] | select(.status=="firing")'

# Check specific alert rules
curl http://localhost:9090/api/v1/rules | jq '.data[] | select(.name=="ContainerCrashed")'
```

---

## Resource Management

### Container Limits (Enforced)

All containers now have `limits` and `reservations`:

- **Limits**: Maximum CPU/memory allowed (hard cap)
- **Reservations**: Guaranteed allocation (soft request)

Example:
```yaml
deploy:
  resources:
    limits:
      cpus: "1"
      memory: 1G
    reservations:
      cpus: "0.25"
      memory: 512M
```

### Monitor Usage

```bash
# Real-time usage
docker stats --no-stream

# High memory consumers
docker ps --format "{{.Names}}\t{{.ID}}" | \
  xargs -I {} docker inspect {} --format '{{.Name}}\t{{.HostConfig.Memory}}' | sort -k2 -nr

# Check system pressure
docker info | grep -A 5 "Docker Root Dir"
```

### Scaling Decisions

- **CPU bottleneck** (>80% sustained): Scale up `OLLAMA_NUM_PARALLEL` or add worker replicas
- **Memory pressure** (>90%): Reduce Prometheus `retention.size` or scale agents
- **Disk space** (<20% free): Run `docker system prune -a` or expand volume

---

## Backup & Restore

### Automated Backups

Backups run daily (default 2 AM):

```bash
# Install cron job
crontab scripts/hypercode-backup.cron

# Run manual backup
bash scripts/backup-volumes.sh

# Backups stored in ./.hypercode-backups/
ls -la .hypercode-backups/
```

### Restore from Backup

```bash
# Stop all services
docker compose down

# Extract backup
tar -xzf .hypercode-backups/hypercode-backup-20260422_020000.tar.gz \
  -C .hypercode-data/

# Restart
docker compose up -d
```

### Critical Volumes

Backed up daily:

- **postgres-data** — Complete database state
- **ollama-data** — LLM models (can be re-downloaded, but time-consuming)
- **agent_memory** — Long-term agent learning
- **grafana-data** — Dashboard definitions
- **prometheus-data** — Metrics history (7-30 days retention)

---

## Debugging Common Issues

### Container Keeps Restarting

```bash
# Check logs
docker logs <container_name> --tail 50 --follow

# Check exit code
docker inspect <container_name> --format '{{.State.ExitCode}}'

# Common codes:
# 0 = normal exit (maybe OOM/health check failed)
# 1 = app error
# 137 = OOM kill (memory limit exceeded)
# 139 = segfault
```

### High Memory Usage

```bash
# Identify offenders
docker stats --no-stream | sort -k4 -hr | head -10

# Check container limits
docker inspect <container> --format '{{.HostConfig.Memory}}'

# Increase if needed (in docker-compose.yml):
deploy:
  resources:
    limits:
      memory: 2G  # was 1G
    reservations:
      memory: 512M
```

### Network Connectivity Issues

```bash
# Test internal connectivity
docker exec <container> curl http://<other_service>:port/health

# Check network membership
docker network inspect <network_name> | grep -A 50 "Containers"

# Verify DNS
docker exec <container> nslookup <service_name>

# Common issue: forgot to add to network in docker-compose.yml
```

### Agent Not Responding

```bash
# Check health
curl http://localhost:8001/health  # project-strategist example

# View logs
docker logs <agent_name> --tail 100

# Check dependencies
docker ps -a | grep -E "redis|postgres|hypercode-core"

# Restart agent (if profile-gated)
docker compose --profile agents up -d <agent_name>
```

---

## Performance Tuning

### PostgreSQL

```bash
# Connection pool status
docker exec postgres psql -U postgres -d hypercode -c "SELECT * FROM pg_stat_activity;"

# If max connections reached:
# 1. Add connection pooling (PgBouncer)
# 2. Or scale Celery workers down
```

### Redis

```bash
# Memory usage
docker exec redis redis-cli INFO memory

# If reaching limit:
# 1. Increase maxmemory in redis command
# 2. Adjust maxmemory-policy (currently: allkeys-lru)
```

### Prometheus

```bash
# Check tsdb size
du -sh $(docker inspect prometheus --format '{{.Mounts | json}}' | jq -r '.[0].Source')

# If too large, reduce retention in docker-compose.yml:
PROMETHEUS_RETENTION_SIZE=5GB  # was 10GB
```

### Ollama (LLM)

```bash
# Check loaded models
curl http://localhost:11434/api/tags

# If memory constrained:
# Reduce OLLAMA_NUM_PARALLEL or OLLAMA_MAX_LOADED_MODELS
# Restart: docker compose restart hypercode-ollama
```

---

## Security Best Practices

### Network Isolation

✓ Enforced:
- `data-net` (internal) — PostgreSQL, Redis only
- `obs-net` (internal) — Prometheus, Grafana, Loki isolated
- `agents-net` — Agents can reach external APIs
- `backend-net` — Core service external API access
- `frontend-net` — Dashboard UI only

### Secrets Management

Currently using `.env` file. For production:

```bash
# Option 1: Use Docker Secrets (Swarm/K8s)
echo "my_secret" | docker secret create my_secret -

# Option 2: HashiCorp Vault
# Configure in docker-compose.yml with external secret provider

# Option 3: GitHub Actions Secrets (CI/CD)
# Never commit .env to version control
```

### Port Exposure

All services bind to `127.0.0.1` (localhost only) — no direct internet exposure.

To expose via reverse proxy:

```yaml
# nginx or caddy in front
# Forward only: /api → 8000, /grafana → 3001
# Require auth at proxy level
```

---

## Maintenance Windows

### Weekly Tasks

- [ ] Review AlertManager for recurring patterns
- [ ] Check disk usage: `docker system df`
- [ ] Verify backup completeness: `ls -la .hypercode-backups/`

### Monthly Tasks

- [ ] Update base images: `docker compose pull`
- [ ] Run security scan: `docker scout cves hypercode-core:latest`
- [ ] Clean old volumes: `docker volume prune --filter 'until=720h'`
- [ ] Review and rotate secrets

### Quarterly Tasks

- [ ] Database maintenance: `VACUUM ANALYZE` (PostgreSQL)
- [ ] Prometheus retention review
- [ ] Load test for scaling needs
- [ ] Disaster recovery drill (restore from backup)

---

## Emergency Procedures

### System Down (Critical Services Offline)

```bash
# 1. Check Docker daemon
systemctl status docker  # or equivalent on your OS

# 2. Check disk space
df -h /

# 3. Check system resources
free -h
top -b -n 1 | head -20

# 4. Check for crash loops
docker events --filter type=container --filter event=die

# 5. Force restart core services
docker compose restart hypercode-core postgres redis
```

### Database Corrupted

```bash
# 1. STOP immediately
docker compose down

# 2. Restore from backup
bash scripts/restore-backup.sh  # (create this from backup.sh template)

# 3. Verify integrity
docker compose up postgres
docker exec postgres pg_dump -U postgres hypercode | head -20

# 4. Restart full stack
docker compose up -d
```

### Memory Leak Detected

```bash
# 1. Identify culprit
docker stats --no-stream | sort -k4 -hr

# 2. Collect logs for debugging
docker logs <container> > debug.log

# 3. Restart container (temporary fix)
docker restart <container>

# 4. Investigate root cause (long-term fix)
# - Check if resource limits should be lower
# - Report issue to dev team
```

---

## Useful Commands Reference

```bash
# Full system restart
docker compose down && docker compose up -d

# View real-time logs from multiple services
docker compose logs -f hypercode-core healer-agent celery-worker

# Execute command in running container
docker exec hypercode-core python -m pytest tests/

# Import/export database
docker exec postgres pg_dump -U postgres hypercode > backup.sql
cat backup.sql | docker exec -i postgres psql -U postgres hypercode

# Access Redis CLI
docker exec -it redis redis-cli

# Access PostgreSQL CLI
docker exec -it postgres psql -U postgres -d hypercode

# View container filesystem
docker inspect <container> --format '{{.GraphDriver.Data.LowerDir}}'
```

---

## Support & Escalation

For issues not covered here, check:

- **Logs**: `docker logs -f <service>`
- **Health checks**: `http://localhost:9093` (AlertManager)
- **Metrics**: `http://localhost:9090` (Prometheus)
- **Dashboards**: `http://localhost:3001` (Grafana)
- **Documentation**: `monitoring/prometheus/hypercode-alerts.yml` (alert definitions)

---

**Last Updated**: 2026-04-22  
**Prepared for**: HyperCode v2.4.2 + 40+ container deployment
