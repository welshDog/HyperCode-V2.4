# ========================================
# RUNBOOK — HyperCode V2.4 Operations Guide
# Quick reference for common tasks + troubleshooting
# ========================================

## 🚀 QUICK START

### Full System Startup (Clean)
```bash
cd HyperCode-V2.4
docker compose pull
docker compose up -d
bash scripts/deploy-validate.sh
```

### Quick Status Check
```bash
docker compose ps
docker stats --no-stream
docker system df
```

---

## 📋 COMMON TASKS

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f hypercode-core
docker compose logs -f backend-specialist

# Last 50 lines
docker compose logs -f --tail 50 hypercode-core

# Follow + filter
docker compose logs -f hypercode-core | grep ERROR
```

### Restart Services
```bash
# Specific service
docker compose restart hypercode-core

# All services
docker compose restart

# Force restart (kill + restart)
docker compose up -d --force-recreate
```

### Rebuild Images
```bash
# Rebuild specific service
docker compose up -d --build hypercode-core

# Rebuild all
docker compose build --no-cache
docker compose up -d
```

### Run Commands Inside Container
```bash
# One-off command
docker compose exec hypercode-core python -m pytest

# Interactive shell
docker compose exec -it hypercode-core /bin/bash

# No TTY (CI/CD)
docker compose exec -T hypercode-core curl http://localhost:8000/health
```

---

## 🔧 TROUBLESHOOTING

### Service Won't Start
```bash
# 1. Check logs
docker compose logs hypercode-core | tail -50

# 2. Check port conflicts
docker ps | grep 8000
lsof -i :8000

# 3. Check disk/memory
docker system df
docker stats

# 4. Restart from clean state
bash scripts/emergency-recover.sh
```

### Memory Pressure / OOM Crashes
```bash
# Check memory usage
docker stats --no-stream

# Identify culprit
docker stats --no-stream --format "table {{.Container}}\t{{.MemPerc}}\t{{.MemUsage}}"

# Increase Docker Desktop memory allocation
# Settings → Resources → Memory (set to 16GB+)

# OR reduce service limits in docker-compose.yml
# (temporarily reduce agent limits from 512M to 256M)
```

### High CPU Usage
```bash
# Check which container
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}"

# Check if it's processing heavy workload
docker compose logs hypercode-core | grep -i "processing\|busy"

# Check for infinite loops in code
docker exec <container> kill -3 <pid>  # Dump stack trace
```

### Database Connection Issues
```bash
# Check postgres
docker compose exec postgres pg_isready -U postgres

# Check connection pool
docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Restart postgres
docker compose restart postgres
```

### Redis Issues
```bash
# Test connectivity
docker compose exec redis redis-cli ping

# Clear all data (CAREFUL!)
docker compose exec redis redis-cli FLUSHALL

# Check memory
docker compose exec redis redis-cli INFO memory
```

### Agent Squad Crashes
```bash
# Restart specific agent
docker compose restart devops-engineer

# Restart all agents
docker compose restart backend-specialist database-architect frontend-specialist qa-engineer devops-engineer

# Check logs for errors
docker compose logs -f devops-engineer | grep -i error
```

---

## 🧹 MAINTENANCE

### Weekly Cleanup
```bash
bash scripts/docker-cleanup.sh
```

### Monthly Deep Clean
```bash
bash scripts/docker-cleanup.sh
docker image prune --all --force
docker builder prune --force --all
docker volume prune --force --all  # ⚠️ CAREFUL — removes data!
```

### Security Scans
```bash
bash scripts/scan-security.sh
cat reports/security/*.json
```

### Disk Space Reclamation
```bash
# See current usage
docker system df

# Reclaim build cache
docker buildx prune --force --keep-storage=5gb

# Full clean (safe)
bash scripts/docker-cleanup.sh
```

---

## 📊 MONITORING

### View Dashboards
- **Grafana (Observability):** http://localhost:3001
- **Dashboard (Web UI):** http://localhost:8088
- **Prometheus (Metrics):** http://localhost:9090

### Check Health Status
```bash
# All services
docker compose ps --format "table {{.Service}}\t{{.Status}}"

# Only unhealthy
docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep unhealthy
```

### Monitor in Real-Time
```bash
# Watch all services
watch -n 2 'docker compose ps'

# Watch resource usage
watch -n 2 'docker stats --no-stream'
```

---

## 🚨 EMERGENCY PROCEDURES

### Full System Recovery
```bash
bash scripts/emergency-recover.sh
```

### Database Recovery (Backup Available)
```bash
# Stop services
docker compose stop

# Restore from backup (if available)
# docker run --rm -v hypercode-v24_postgres-data:/data -v /path/to/backup:/backup \
#   postgres:15 pg_restore -U postgres -d hypercode /backup/hypercode.dump

# Start services
docker compose up -d
```

### Network Issues
```bash
# Inspect network
docker network inspect hypercode_agents_net

# Restart networking
docker compose down
docker network prune --force
docker compose up -d
```

### Port Conflicts
```bash
# Find what's using port
lsof -i :8000
netstat -tlnp | grep 8000

# Restart conflicting service
docker compose restart hypercode-core

# OR use different port in .env
# CORE_PORT=8001
docker compose up -d
```

---

## 📝 DEPLOYMENT CHECKLIST

Before going live:
- [ ] Run `deploy-validate.sh` and confirm all green
- [ ] Check logs: `docker compose logs | grep -i error` (no errors)
- [ ] Test API: `curl http://localhost:8000/health`
- [ ] Test agents: Verify at least 2-3 agents responding
- [ ] Check disk: `docker system df` (should be < 80% full)
- [ ] Run security scan: `bash scripts/scan-security.sh`
- [ ] Monitor for 10 minutes: No crashes, stable memory

---

## 🔗 USEFUL LINKS

- **Docker Docs:** https://docs.docker.com
- **Docker Compose:** https://docs.docker.com/compose
- **Prometheus:** https://prometheus.io/docs
- **Grafana:** https://grafana.com/docs
- **HyperCode Repo:** Check GitHub/internal documentation

---

## 📞 SUPPORT

If issues persist:
1. Check runbook above
2. Review full logs: `docker compose logs <service> | tail -100`
3. Run: `bash scripts/emergency-recover.sh`
4. Check disk: `docker system df`
5. Check memory: `docker stats`

---

**Last Updated:** 2026-05-25
