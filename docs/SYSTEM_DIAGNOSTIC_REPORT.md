# 🔧 SYSTEM DIAGNOSTIC & REPAIR REPORT
**Date**: March 21, 2026  
**Issue Detected**: Multiple containers restarting / unhealthy  
**Status**: 🔴 **PROBLEMS FOUND** — Let's fix them

---

## 🚨 ISSUES DETECTED

### **CRITICAL: Containers Restarting** (4 containers)

| Container | Status | Issue | Fix |
|-----------|--------|-------|-----|
| **healer-agent** | Restarting (1) | Exit code 1 | Config/dependency issue |
| **tempo** | Restarting (1) | Exit code 1 | Config issue |
| **cadvisor** | Restarting (255) | Exit code 255 | Permission/mount issue |
| **node-exporter** | Restarting (2) | Exit code 2 | Argument/flag issue |
| **hypercode-dashboard** | Restarting (127) | Exit code 127 | Missing command issue |

### **MEDIUM: Unhealthy Containers** (1 container)

| Container | Status | Issue |
|-----------|--------|-------|
| **celery-worker** | Unhealthy | Health check failing |

### **INFO: Not Running** (1 container)

| Container | Status | Note |
|-----------|--------|------|
| **hypercode-ollama** | Exited (255) | Was stopped for cooling |

---

## 🔍 DETAILED ANALYSIS

### **1. healer-agent (RESTARTING)**
**Status**: `Restarting (1) 7 seconds ago`  
**Image**: hypercode-v20-healer-agent  
**Command**: `uvicorn healer.main:app --...`

**Likely Causes**:
- Missing environment variable (DOCKER_HOST, REDIS_URL)
- Missing volume mount (/var/run/docker.sock)
- Connection error to hypercode-core
- Module import error

**Fix**:
```bash
docker logs healer-agent --tail 50  # Check exact error
# Then: docker-compose stop healer-agent && docker-compose up -d healer-agent
```

---

### **2. tempo (RESTARTING)**
**Status**: `Restarting (1) 21 seconds ago`  
**Image**: grafana/tempo:latest  
**Command**: `/tempo -config.file=...`

**Likely Causes**:
- Config file missing or invalid
- YAML syntax error
- Port conflict (3200, 4317, 4318)

**Fix**:
```bash
docker logs tempo --tail 50  # Check config error
# Check monitoring/tempo/tempo.yaml exists and is valid YAML
```

---

### **3. cadvisor (RESTARTING)**
**Status**: `Restarting (255) 4 seconds ago`  
**Image**: gcr.io/cadvisor/cadvisor:latest

**Likely Causes**:
- Missing volumes (cgroup, sys, proc not mounted)
- Permission denied on docker.sock
- Device permissions issue

**Fix**:
```bash
# cadvisor needs specific mounts:
docker run -d \
  --name cadvisor \
  -v /:/rootfs:ro \
  -v /var/run:/var/run:ro \
  -v /sys:/sys:ro \
  -v /var/lib/docker/:/var/lib/docker:ro \
  -p 8090:8080 \
  gcr.io/cadvisor/cadvisor:latest
```

---

### **4. node-exporter (RESTARTING)**
**Status**: `Restarting (2) 19 seconds ago`  
**Image**: prom/node-exporter:latest

**Likely Causes**:
- Invalid flags in docker-compose command
- Missing mount point
- Port conflict (9100)

**Fix**:
```bash
docker logs node-exporter --tail 20  # Check flags
# Or restart: docker-compose restart node-exporter
```

---

### **5. hypercode-dashboard (RESTARTING)**
**Status**: `Restarting (127) 54 seconds ago`  
**Image**: hypercode-v20-dashboard:latest

**Likely Causes**:
- Exit code 127 = "command not found"
- Entrypoint or CMD broken
- Missing dependencies

**Fix**:
```bash
docker logs hypercode-dashboard --tail 50  # Check error
# Rebuild if needed: docker-compose build dashboard --no-cache
docker-compose up -d hypercode-dashboard
```

---

### **6. celery-worker (UNHEALTHY)**
**Status**: `Up 11 minutes (unhealthy)`  
**Image**: hypercode-v20-celery-worker

**Likely Causes**:
- Health check failing (celery not responding to ping)
- Worker crashed but container still running
- Redis/Postgres connection issue

**Fix**:
```bash
docker logs celery-worker --tail 100  # Check worker status
docker exec celery-worker python -m celery -A app.core.celery_app inspect ping
# If fails: docker-compose restart celery-worker
```

---

### **7. hypercode-ollama (EXITED)**
**Status**: `Exited (255) 11 minutes ago`  
**Note**: This was stopped for cooling - can restart when needed

**To Restart**:
```bash
docker-compose up -d hypercode-ollama
```

---

## ✅ QUICK FIX SCRIPT

Run these commands in order:

```bash
cd ./HyperCode-V2.0

# 1. Check each failing container's logs
echo "=== HEALER-AGENT ==="
docker logs healer-agent --tail 30

echo "=== TEMPO ==="
docker logs tempo --tail 30

echo "=== CADVISOR ==="
docker logs cadvisor --tail 30

echo "=== NODE-EXPORTER ==="
docker logs node-exporter --tail 30

echo "=== DASHBOARD ==="
docker logs hypercode-dashboard --tail 30

echo "=== CELERY-WORKER ==="
docker logs celery-worker --tail 30
```

---

## 🔧 STEP-BY-STEP FIXES

### **Fix Option 1: Restart Everything**
```bash
cd ./HyperCode-V2.0

# Stop all
docker-compose down

# Wait 5 seconds
sleep 5

# Start core services only (safest)
docker-compose up -d hypercode-core postgres redis

# Wait for them to be healthy
sleep 30

# Start other services
docker-compose up -d

# Check status
docker-compose ps
```

### **Fix Option 2: Restart Only Broken Services**
```bash
cd ./HyperCode-V2.0

docker-compose restart healer-agent
docker-compose restart tempo
docker-compose restart cadvisor
docker-compose restart node-exporter
docker-compose restart hypercode-dashboard
docker-compose restart celery-worker

# Wait 30s for them to stabilize
sleep 30

# Check status
docker-compose ps | grep -E "healer|tempo|cadvisor|node-exporter|dashboard|celery"
```

### **Fix Option 3: Targeted Fixes**

**For healer-agent**:
```bash
docker-compose stop healer-agent
docker-compose logs healer-agent --tail 50
# Fix based on error shown
docker-compose up -d healer-agent
```

**For tempo**:
```bash
# Check config file exists
ls -la ./monitoring/tempo/tempo.yaml
# If missing, check git or recreate
docker-compose restart tempo
```

**For cadvisor**:
```bash
# cadvisor is optional (monitoring only)
# Safe to remove if causing issues
docker-compose stop cadvisor
# Or restart with fresh config
docker-compose restart cadvisor
```

**For node-exporter**:
```bash
docker-compose restart node-exporter
```

**For hypercode-dashboard**:
```bash
# Rebuild if restarting doesn't work
docker-compose build dashboard --no-cache
docker-compose up -d hypercode-dashboard
```

**For celery-worker**:
```bash
docker-compose restart celery-worker
# Wait 30s for health check to pass
sleep 30
docker-compose ps celery-worker
```

---

## 🟢 HEALTHY CONTAINERS (Good!)

These are running fine:

```
✅ hypercode-core       (healthy)
✅ postgres             (healthy)
✅ redis                (healthy)
✅ prometheus           (healthy)
✅ grafana              (healthy)
✅ loki                 (healthy)
✅ minio                (healthy)
✅ chroma               (healthy)
✅ test-agent           (healthy)
✅ throttle-agent       (healthy)
✅ super-hyper-broski-agent (healthy)
✅ backend-specialist   (healthy)
✅ crew-orchestrator    (healthy)
✅ + 10 more services
```

---

## 📊 CURRENT STATUS SUMMARY

| Category | Count | Status |
|----------|-------|--------|
| **Running & Healthy** | 30+ | 🟢 OK |
| **Running but Unhealthy** | 1 | 🟡 celery-worker |
| **Restarting** | 4 | 🔴 healer, tempo, cadvisor, node-exporter, dashboard |
| **Exited (On Purpose)** | 1 | ⚪ hypercode-ollama (cooling) |
| **Dead** | 2+ | ⚪ Old containers |

---

## 💡 WHY THIS HAPPENED

The UUID `9C7EF2C2-82BE-4E7F-BB40-113DAFD6143D/20260321174516` is likely:
- A container restart ID
- A volume mount point
- A system event identifier
- Related to something you tried that caused a restart cascade

The restarting containers suggest:
- Configuration file changes
- Environment variable issues
- Volume mount problems
- Connection timeouts to dependencies

---

## 🎯 RECOMMENDED ACTION PLAN

### **Immediate (Do Now)**:
1. Check logs for each failing service: `docker logs <container> --tail 50`
2. Identify root cause of restarts
3. Run `docker-compose ps` to see current state
4. Pick Fix Option 1, 2, or 3 above

### **Short-term**:
1. Verify all critical services healthy (core, postgres, redis)
2. Fix restarting containers one by one
3. Test critical endpoints work

### **After Fixes**:
1. Run full health check
2. Create new status report
3. Document what caused the issue
4. Update monitoring

---

## 📝 WHAT TO TRY FIRST

**Best approach (lowest risk)**:

```bash
cd ./HyperCode-V2.0

# 1. Check one failing service
docker logs healer-agent --tail 50

# 2. If it's a config issue, check config exists
ls -la ./agents/healer/

# 3. If it's an env issue, check docker-compose.yml
grep -A 20 "healer-agent:" docker-compose.yml

# 4. Try restarting just that one
docker-compose restart healer-agent

# 5. Check status
docker-compose ps healer-agent

# 6. If still failing, get more logs
docker logs healer-agent --tail 200
```

---

**What was the error message or what were you trying?** Let me know and I can give you specific fixes!

*Diagnostic Report*  
*Gordon — Docker AI Assistant*  
*March 21, 2026*
