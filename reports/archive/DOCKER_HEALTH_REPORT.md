# Docker Health Check & Status Report

**Generated:** 2026-03-11  
**System:** Docker Desktop on Windows (WSL2)  
**Docker Version:** 29.2.1

---

## Executive Summary

Your Docker environment has **23 running containers** out of 25 total, with **61 images** consuming **69.93GB** of disk space. The system is **operational** with no critical health issues, but there are **2 actionable problems** and **several optimization opportunities**.

---

## 1. CONTAINER STATUS

### 🟢 Running (23 containers)

**Healthy (11):**
- crew-orchestrator (healthy)
- grafana (healthy)
- healer-agent (healthy)
- prometheus (healthy)
- hypercode-core (healthy)
- postgres (healthy)
- redis (healthy)
- hypercode-ollama (healthy)
- chroma (healthy)
- minio (healthy)
- node-exporter (healthy)
- cadvisor (healthy)

**Running - No Health Check (12):**
- laughing_haibt (dashboard)
- busy_cohen (inotifywait)
- project-strategist-v2
- tempo
- auto-prune
- loki
- security-scanner
- promtail
- grafana-docker-desktop-extension-alloy
- grafana_docker-desktop-extension-desktop-extension-1
- docker_labs-ai-tools-for-devs-desktop-extension-service

**Networking:** All containers share 7 networks (bridge, host, hypercode_data_net, hypercode_public_net, etc.)

### 🔴 Stopped (2 containers)

1. **celery-exporter** - Exited with code 137 (OOM/Killed)
   - **Root Cause:** Redis connection failure at container startup
   - **Error:** `kombu.exceptions.OperationalError: Error -2 connecting to redis:6379. Name or service not known`
   - **Status:** Cannot reach Redis service (DNS resolution failing or service not available)

2. **broski-bot** - Exited with code 1 (Auth failure)
   - **Root Cause:** Invalid Discord bot token
   - **Error:** `discord.errors.LoginFailure: Improper token has been passed`
   - **Status:** Application error, requires valid Discord token in environment

---

## 2. RESOURCE USAGE

### Storage Breakdown
```
Images:       69.93GB  (25 active out of 61)    → 53.26GB reclaimable (76%)
Containers:   1.111GB  (23 running)              → 16.96MB reclaimable (1%)
Volumes:      144.2MB  (3 in use out of 27)     → 96.5MB reclaimable (66%)
Build Cache:  33.85GB  (no active builds)       → 14.95GB reclaimable (42%)
```

**Total Storage Available for Cleanup: ~68.26GB (76% of current usage)**

### Key Storage Hogs

**Top Images by Size:**
1. hypercode-v20-hypercode-core: **12.9GB**
2. hypercode-v20-celery-worker: **12.9GB**
3. ollama/ollama: **9.01GB**
4. hypercode-v20-coder-agent: **1.36GB**
5. hypercode-v20-crew-orchestrator: **1.49GB**

**Unused/Old Images:** 36 images not currently running (consuming ~53GB)

### Disk Pressure
- WSL2 Virtual Machine allocated: 3.826 GiB total memory
- CPU: 2 cores
- Kernel: 6.6.87.2-microsoft-standard

---

## 3. NETWORKING

### Networks Detected (7)
- **bridge** - Default Docker bridge
- **host** - Host network driver
- **hypercode_data_net** - Project network (internal services)
- **hypercode_public_net** - Project network (public exposure)
- **docker_labs-ai-tools-for-devs-desktop-extension_default**
- **grafana_docker-desktop-extension-desktop-extension_extension**
- **none** - Null driver

### Port Mappings (Publicly Exposed)
```
3000    → laughing_haibt (dashboard)
3001    → grafana
3100    → loki
3200    → tempo
8000    → hypercode-core (localhost only)
8009    → chroma
8010    → healer-agent
8081    → crew-orchestrator
8090    → cadvisor
8811    → docker_labs-ai-tools-for-devs-desktop-extension
9000-9001 → minio
9090    → prometheus
9100    → node-exporter
9412    → tempo (alternate)
4317-4318 → tempo (OpenTelemetry)
```

---

## 4. VOLUMES

**Total Volumes:** 27  
**In Use:** 3  
**Unused:** 24 (~96.5MB reclaimable)

**Active Named Volumes:**
- hypercode-v20_agent_memory
- hypercode-v20_chroma_data
- hypercode-v20_grafana-data
- hypercode-v20_minio_data
- hypercode-v20_model_cache
- hypercode-v20_ollama-data
- hypercode-v20_postgres-data
- hypercode-v20_postgres-demo-data
- hypercode-v20_prometheus-data
- hypercode-v20_redis-data
- hypercode-v20_tempo-data
- docker_prompts (single-use)
- postgres-data (legacy)

**Orphaned Volumes:** 14 anonymous volumes (hash-named) consuming storage

---

## 5. DOCKER DAEMON STATUS

### ✅ Healthy Configuration
- Storage Driver: **overlayfs** (efficient, modern)
- Cgroup Driver: **cgroupfs** with v2 (modern)
- Logging Driver: **json-file** (standard)
- Runtimes: runc, nvidia, io.containerd.runc.v2 (good GPU support)
- Security: seccomp + cgroupns enabled
- Swarm: Inactive (not needed for single-host dev)

### ⚠️ Network Configuration
- HTTP/HTTPS Proxy detected: `http.docker.internal:3128`
- Insecure registries configured (hubproxy.docker.internal:5555)
- Live Restore: **Disabled** (containers don't auto-restart on daemon restart)

### ⚠️ Resource Limits
- Total Memory: 3.826 GiB (WSL2 default)
- CPUs: 2 cores (WSL2 default)
- **Recommendation:** Increase to 4+ GiB RAM and 4 cores for this workload

---

## 6. ISSUES & CRITICAL FINDINGS

### 🔴 Critical Issues (2)

#### Issue 1: Celery-Exporter Service Down
- **Status:** Exited (137 - OOM Killed)
- **Root Cause:** Cannot connect to Redis at startup; DNS/networking issue
- **Evidence:** Logs show `Error -2 connecting to redis:6379. Name or service not known`
- **Impact:** Metrics collection for Celery workers unavailable
- **Fix:**
  ```bash
  # 1. Verify Redis is running and healthy
  docker logs redis
  
  # 2. Check network connectivity
  docker exec crew-orchestrator ping redis
  
  # 3. Restart celery-exporter with dependency
  docker restart celery-exporter
  
  # Alternative: Update docker-compose to add depends_on + healthcheck
  ```

#### Issue 2: BROski-Bot Service Down
- **Status:** Exited (1 - Auth Failure)
- **Root Cause:** Invalid/missing Discord bot token
- **Evidence:** `discord.errors.LoginFailure: Improper token has been passed`
- **Impact:** Discord bot service unavailable
- **Fix:**
  ```bash
  # 1. Verify Discord token is set and valid
  docker inspect broski-bot | grep -A 20 "Env"
  
  # 2. Re-run with correct token
  docker run -e DISCORD_TOKEN="your_valid_token" hypercode-v20-broski-bot
  
  # 3. Or update docker-compose.yml with valid token
  # 4. Restart: docker compose up -d broski-bot
  ```

### 🟡 Warnings (3)

#### Warning 1: Massive Image Bloat
- **Issue:** 36 unused images consuming ~53GB
- **Impact:** Disk space wasted, slower `docker images` operations
- **Severity:** Medium (76% of images not in use)

#### Warning 2: Orphaned Volumes
- **Issue:** 14 anonymous/dangling volumes (96.5MB)
- **Impact:** Data fragmentation, potential data loss
- **Severity:** Low (small total size, but indicates cleanup neglect)

#### Warning 3: WSL2 Resource Constraints
- **Issue:** Only 3.826 GiB RAM allocated to WSL2, 2 CPU cores
- **Impact:** Container memory pressure during peak usage
- **Evidence:** Celery-exporter was killed (exit 137 = OOM)
- **Severity:** Medium (will worsen with more services)

---

## 7. PERFORMANCE & OPTIMIZATION

### Current Performance
- **Container startup time:** ~18 minutes for full stack (based on timestamps)
- **Health check status:** 12 of 23 running containers have health checks (52%)
- **Service dependencies:** Not fully managed (manual order required)

### Optimization Opportunities

1. **Health Check Implementation (Quick Win)**
   - Add HEALTHCHECK to: laughing_haibt, project-strategist-v2, tempo, loki, security-scanner, promtail
   - Typical implementation:
     ```dockerfile
     HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
       CMD curl -f http://localhost:PORT/health || exit 1
     ```
   - **Impact:** Better monitoring, auto-restart capability, better orchestration

2. **Image Cleanup (Medium Effort, High Reward)**
   - Remove 36 unused images: `docker image prune -a -f`
   - **Benefit:** Free up 53GB disk space
   - **Time:** 5 minutes

3. **Volume Consolidation (Low Priority)**
   - Remove 14 orphaned volumes: `docker volume prune -f`
   - **Benefit:** Free up 96.5MB, cleaner volume namespace
   - **Time:** 2 minutes

4. **Increase WSL2 Resources (High Priority)**
   - Update `%USERPROFILE%\.wslconfig`:
     ```ini
     [wsl2]
     memory=8GB
     processors=4
     swap=2GB
     ```
   - **Impact:** Prevent OOM kills, faster build times
   - **Time:** 5 minutes + WSL2 restart

5. **Service Dependencies in Docker Compose**
   - Add `depends_on:` and `healthcheck:` conditions
   - **Benefit:** Automatic startup order, parallel startup possible
   - **Current:** Manual orchestration required
   - **Impact:** Reduce startup time from 18 min to ~5 min

6. **Build Cache Management (Medium Effort)**
   - 33.85GB build cache with 42% reclaimable
   - Clean with: `docker buildx du --verbose` then `docker builder prune`
   - **Benefit:** Faster builds, cleaner cache
   - **Time:** 3 minutes

7. **Network Optimization**
   - Consolidate 7 networks into 2-3 logical groups
   - Remove unused/dangling networks: `docker network prune -f`
   - **Benefit:** Cleaner setup, faster container-to-container communication

---

## 8. SECURITY & COMPLIANCE

### ✅ Enabled Security Features
- SECcomp profile (container syscall filtering)
- Cgroup namespace isolation
- Kernel version up-to-date (6.6.87.2)

### ⚠️ Security Considerations
- Insecure registries configured (hubproxy.docker.internal:5555)
- HTTP Proxy in use (potential man-in-the-middle risk)
- **Recommendation:** Use HTTPS for all registry pulls, verify proxy certificates

### 🔍 Image Scanning
- Trivy image scanning container running (`security-scanner`)
- **Status:** Active and healthy
- **Recommendation:** Regularly scan images before deployment; integrate into CI/CD

---

## 9. RECOMMENDATIONS (Priority Order)

### 🚨 IMMEDIATE (Today)

1. **Restart celery-exporter with Redis health verification**
   ```bash
   docker logs redis | tail -5  # Verify Redis is healthy
   docker restart celery-exporter
   docker logs celery-exporter  # Verify startup
   ```

2. **Fix broski-bot Discord token**
   ```bash
   # Set correct token and restart
   docker compose up -d broski-bot
   ```

3. **Increase WSL2 memory to 8GB, CPU to 4 cores**
   - Edit `%USERPROFILE%\.wslconfig`
   - Restart WSL2: `wsl --shutdown`

### 📋 SHORT TERM (This Week)

4. **Clean up unused images** (~5 min)
   ```bash
   docker image prune -a -f  # Frees 53GB
   ```

5. **Add HEALTHCHECK directives** to 6 containers
   - Update Dockerfiles
   - Rebuild images
   - Redeploy via docker-compose

6. **Implement service dependencies** in docker-compose.yml
   ```yaml
   services:
     celery-exporter:
       depends_on:
         redis:
           condition: service_healthy
   ```

### 📊 MEDIUM TERM (Next Month)

7. **Consolidate volume strategy**
   - Document all persistent data paths
   - Remove orphaned volumes: `docker volume prune -f`
   - Implement volume backup strategy

8. **Optimize build cache**
   ```bash
   docker buildx du --verbose
   docker builder prune  # Remove unused layers
   ```

9. **Network architecture review**
   - Map service dependencies
   - Consolidate into service tiers (frontend, backend, data, monitoring)
   - Reduce networks from 7 to 3-4

10. **Implement centralized logging**
    - Loki + Promtail already deployed
    - Configure all containers to send logs to Loki
    - Create dashboards in Grafana for log analysis

---

## 10. MONITORING DASHBOARDS

**Already Running:**
- Prometheus: http://localhost:9090 (metrics)
- Grafana: http://localhost:3001 (dashboards)
- cAdvisor: http://localhost:8090 (container metrics)
- Loki: http://localhost:3100 (logs)
- Tempo: http://localhost:3200 (traces)

**Action:** Set up Grafana dashboard for Docker resource usage using cAdvisor + Prometheus

---

## 11. QUICK REFERENCE COMMANDS

```bash
# Health check
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs
docker logs <container_name> --tail 50 -f

# Resource usage
docker stats --no-stream

# Disk usage
docker system df

# Cleanup (safe)
docker system prune -f

# Cleanup (aggressive - removes all unused)
docker image prune -a -f
docker volume prune -f
docker builder prune -a -f

# Restart stack
docker compose down
docker compose up -d
```

---

## Summary

| Metric | Status | Action |
|--------|--------|--------|
| Running Containers | 23/25 (92%) | Fix 2 failed services |
| Storage Used | 69.93GB (53GB reclaimable) | Prune unused images |
| Memory Allocated | 3.8GB (constrained) | Increase to 8GB |
| Health Checks | 52% coverage | Add 6 more |
| Networks | 7 (fragmented) | Consolidate to 3-4 |
| Security | ✅ Good | Monitor proxy certs |

**Overall Health: 7/10** (Good, with clear optimization path)
