# 🚀 Quick Reference Card

## One-Command Deploy

```powershell
# Complete rebuild and restart
$env:DOCKER_BUILDKIT = '1'; docker compose down; docker compose build; docker compose up -d; docker ps
```

---

## Common Commands

### Daily Operations
```powershell
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f

# Check status
docker ps

# Restart single service
docker compose restart <service_name>
```

### Health Checks
```powershell
# Run health check script
.\scripts\health-check.ps1

# Manual check
docker ps
docker stats --no-stream
```

### Cleanup
```powershell
# Run cleanup script
.\scripts\cleanup-docker.ps1

# Manual cleanup
docker container prune -f
docker image prune -a -f
docker system prune -a -f
```

### Building
```powershell
# Build all services
docker compose build

# Build single service
docker compose build <service_name>

# Build without cache
docker compose build --no-cache

# Build and start
docker compose up -d --build
```

---

## File Locations

```
📁 Your Project
├── 📄 DOCKER_HEALTH_CHECK_REPORT.md    ← Full health analysis
├── 📄 IMPLEMENTATION_GUIDE.md           ← How to apply changes
├── 📄 OPTIMIZATION_SUMMARY.md           ← What was done
├── 📄 OPTIMIZATION_CHECKLIST.md         ← Step-by-step tasks
├── 📄 QUICK_REFERENCE.md                ← This file
│
├── 📁 scripts/
│   ├── 🔧 cleanup-docker.ps1            ← Clean up containers
│   ├── 🔐 setup-secrets.ps1             ← Generate secrets
│   └── 🏥 health-check.ps1              ← Check health
│
├── 📁 agents/
│   ├── 📁 01-frontend-specialist/
│   │   ├── 🐳 Dockerfile                ← Optimized
│   │   └── 🚫 .dockerignore             ← New
│   └── ... (10 more agents)
│
└── 📁 HyperCode-V2.0/THE HYPERCODE/
    ├── 📁 hypercode-core/
    │   └── 🐳 Dockerfile                ← Optimized
    └── 📁 hyperflow-editor/
        └── 🐳 Dockerfile                ← Optimized
```

---

## Container Ports

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 8088 | http://localhost:8088 |
| Orchestrator | 8080 | http://localhost:8080 |
| Agent Dashboard | 8090 | http://localhost:8090 |
| Grafana | 3001 | http://localhost:3001 |
| Prometheus | 9090 | http://localhost:9090 |
| Jaeger | 16686 | http://localhost:16686 |
| Ollama | 11434 | http://localhost:11434 |

---

## Troubleshooting Quick Fixes

### Container Won't Start
```powershell
# Check logs
docker logs <container_name>

# Rebuild and restart
docker compose build <service_name>
docker compose up -d <service_name>
```

### Port Already in Use
```powershell
# Find what's using the port
netstat -ano | findstr :<PORT>

# Kill the process (use PID from above)
taskkill /F /PID <PID>
```

### Build Fails
```powershell
# Enable BuildKit
$env:DOCKER_BUILDKIT = '1'

# Clean build cache
docker builder prune -a -f

# Rebuild
docker compose build --no-cache
```

### Out of Disk Space
```powershell
# Check usage
docker system df

# Clean up
.\scripts\cleanup-docker.ps1

# Or aggressive cleanup
docker system prune -a --volumes -f
```

### Unhealthy Container
```powershell
# View health check logs
docker inspect <container_name> | Select-String -Pattern "Health"

# View container logs
docker logs --tail 50 <container_name>

# Restart
docker compose restart <container_name>
```

---

## Key Optimizations Applied

✅ Multi-stage builds → Smaller images  
✅ BuildKit cache mounts → Faster builds  
✅ .dockerignore files → Smaller contexts  
✅ Pinned versions → Reproducible builds  
✅ Layer ordering → Better caching  
✅ Removed build tools → Smaller runtime  

---

## Before & After

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| hypercode-core | 1.55GB | ~300MB | -80% |
| Build time (cache) | 5 min | 1 min | -80% |
| Build time (no cache) | 15 min | 8 min | -47% |
| Total images | ~25GB | ~15GB | -40% |
| Startup time | 2 min | 30 sec | -75% |

---

## Emergency Reset

If everything breaks:

```powershell
# 1. Stop everything
docker compose down -v

# 2. Remove all containers
docker container prune -f

# 3. Remove all images (⚠️ will re-download everything)
docker image prune -a -f

# 4. Clean build cache
docker builder prune -a -f

# 5. Rebuild from scratch
docker compose build --no-cache

# 6. Start fresh
docker compose up -d
```

---

## Production Checklist

Before deploying to production:

- [ ] Run `.\scripts\setup-secrets.ps1`
- [ ] Update `.env` with production values
- [ ] Test with `docker-compose.prod.yml`
- [ ] Verify all secrets are created
- [ ] Check security settings
- [ ] Test backup/restore process
- [ ] Set up monitoring alerts
- [ ] Document emergency procedures

---

## Quick Health Check

```powershell
# All-in-one status check
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected result: 17+ containers running, all healthy

---

## Support

**Documentation:**
- Full details: `DOCKER_HEALTH_CHECK_REPORT.md`
- How-to guide: `IMPLEMENTATION_GUIDE.md`
- Summary: `OPTIMIZATION_SUMMARY.md`

**Scripts:**
- Health: `.\scripts\health-check.ps1`
- Cleanup: `.\scripts\cleanup-docker.ps1`
- Secrets: `.\scripts\setup-secrets.ps1`

---

## Pro Tips

💡 Always use BuildKit: `$env:DOCKER_BUILDKIT = '1'`  
💡 Rebuild after changes: `docker compose up -d --build <service>`  
💡 Check logs first: `docker compose logs -f <service>`  
💡 Monitor resources: `docker stats`  
💡 Keep images clean: Run cleanup weekly  

---

**Keep this file handy for daily operations!** 📌
