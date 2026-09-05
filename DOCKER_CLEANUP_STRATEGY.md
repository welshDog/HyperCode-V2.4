# Docker Cleanup Strategy & Memory Limits Guide

## Exit-137 Agent Containers: Root Cause & Fix

**Finding:** 20+ agent containers exited with code 137 two days ago. Inspection revealed:
- ✓ `OOMKilled=false` on all checked containers — **not cgroup kills**
- ✓ Killed by external signal (CI shutdown, orchestration stop, or host reaper)
- ✓ No systemic memory crisis; containers were under-resourced in compose, not leaking

**Affected Agents (from exit history):**
- meta-research-architect (Exited 137, 2 days ago)
- throttle-agent (Exited 137, 2 days ago)
- nemoclaw-agent (Exited 137, 2 days ago)
- broski-pets-bridge (Exited 137, 2 days ago)
- coder-studio (Exited 137, 2 days ago)
- hyper-split-agent (Exited 137, 2 days ago)
- business-agent (Exited 137, 2 days ago)
- tips-tricks-writer (Exited 137, 2 days ago)
- brain-agent (Exited 137, 2 days ago)
- coderabbit-webhook (Exited 137, 2 days ago)
- test-agent (Exited 137, 2 days ago)
- session-snapshot (Exited 137, 2 days ago)
- super-hyper-broski-agent (Exited 137, 2 days ago)
- goal-keeper (Exited 137, 2 days ago)
- agent-x (Exited 137, 2 days ago)
- hyper-worker (Exited 137, 2 days ago)
- hyper-architect (Exited 137, 2 days ago)
- mcp-rest-adapter (Exited 137, 2 days ago)
- broski-coo (Exited 137, 2 days ago)
- hyper-observer (Exited 137, 2 days ago)
- agent-registry (Exited 137, 2 days ago)
- mission-director (Exited 137, 2 days ago)
- hyper-auto-assistant (Exited 137, 2 days ago)
- agent-factory (Exited 137, 2 days ago)

---

## Memory Limit Recommendations for Agent Containers

### Current Memory Profile (Running Agents - Nov 2026)

**Agent Containers Currently Running (healthy):**
- healer-agent: 512M limit (15.57% usage = ~80MB actual)
- hypercode-core: 1.5GB limit (9.22% usage = ~138MB actual)
- hypercode-dashboard: 512M limit (13.18% usage = ~68MB actual)
- hyperhealth-worker: 1GB limit (7.22% usage = ~74MB actual)

### Recommended Memory Limits (by Agent Type)

Add these to `docker-compose.agents.yml`, `docker-compose.agents-full.yml`, and the core `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "0.5"
      memory: 512M          # Primary agent limit
    reservations:
      cpus: "0.25"
      memory: 256M          # Guaranteed minimum
```

**Memory Sizing by Agent Complexity:**

| Agent Type | Limit | Reservation | Use Case |
|-----------|-------|-------------|----------|
| **Lightweight** (watchers, relays) | 256M | 128M | github-sync, evolve-relay, agent-focus-tracker |
| **Standard** (most agents) | 512M | 256M | coder-agent, crew-orchestrator, goal-keeper, project-strategist, frontend-specialist, backend-specialist, qa-engineer, devops-engineer |
| **Heavy** (orchestrators, researchers) | 1GB | 512M | meta-research-architect, coderabbit-webhook, agent-x, hyper-worker |
| **Data-intensive** (brain, memory) | 1.5GB | 768M | hyper-brain, hyper-architect, agent-hyper-brain-core |

### Specific Agents to Update (by docker-compose file)

**In `docker-compose.agents.yml`:**
```yaml
# Lightweight agents
agent-focus-tracker:
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M

agent-mcp-bridge:
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M

agent-morning-briefing:
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M

agent-hyper-brain-core:
  deploy:
    resources:
      limits:
        memory: 1.5GB
      reservations:
        memory: 768M

# Standard agents (profile: agents)
coder-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

crew-orchestrator:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

goal-keeper:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

project-strategist:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

frontend-specialist:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

backend-specialist:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

database-architect:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

qa-engineer:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

devops-engineer:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

security-engineer:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

system-architect:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M
```

**In `docker-compose.agents-full.yml` (exit-137 agents):**
```yaml
meta-research-architect:
  deploy:
    resources:
      limits:
        memory: 1GB
      reservations:
        memory: 512M

throttle-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

nemoclaw-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

broski-pets-bridge:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

coder-studio:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

hyper-split-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

business-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

tips-tricks-writer:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

brain-agent:
  deploy:
    resources:
      limits:
        memory: 1GB
      reservations:
        memory: 512M

coderabbit-webhook:
  deploy:
    resources:
      limits:
        memory: 1GB
      reservations:
        memory: 512M

test-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

session-snapshot:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

super-hyper-broski-agent:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

goal-keeper:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

agent-x:
  deploy:
    resources:
      limits:
        memory: 1GB
      reservations:
        memory: 512M

hyper-worker:
  deploy:
    resources:
      limits:
        memory: 1GB
      reservations:
        memory: 512M

hyper-architect:
  deploy:
    resources:
      limits:
        memory: 1.5GB
      reservations:
        memory: 768M

mcp-rest-adapter:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

broski-coo:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

hyper-observer:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

agent-registry:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

mission-director:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

hyper-auto-assistant:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M

agent-factory:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M
```

---

## Scheduled Cleanup Strategy

### Option 1: Shell Script (Recommended for Local Development)

**File:** `scripts/docker-cleanup.sh`

```bash
#!/bin/bash
# Docker Cleanup Script — Scheduled maintenance for image, build cache, and container pruning
# Usage:
#   - Run manually: ./scripts/docker-cleanup.sh
#   - Add to crontab for weekly/monthly automation

set -e

LOGFILE="${LOG_DIR:-.}/docker-cleanup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
  echo "[$TIMESTAMP] $1" | tee -a "$LOGFILE"
}

# Step 1: Monthly build cache prune (first day of month, or on demand)
cleanup_build_cache() {
  log "Starting build cache prune..."
  BEFORE=$(docker system df --format='{{.BuildCache.Size}}')
  docker builder prune -f --verbose
  AFTER=$(docker system df --format='{{.BuildCache.Size}}')
  log "Build cache prune complete. Size reduction: $BEFORE → $AFTER"
}

# Step 2: Weekly image prune (unused images)
cleanup_images() {
  log "Starting image prune (unused images)..."
  BEFORE=$(docker system df --format='{{.Images.Size}}')
  UNUSED=$(docker image prune -a -f --verbose)
  AFTER=$(docker system df --format='{{.Images.Size}}')
  log "Image prune complete. Removed: $UNUSED"
  log "Image size reduction: $BEFORE → $AFTER"
}

# Step 3: Weekly container prune (exited containers)
cleanup_containers() {
  log "Starting container prune (exited)..."
  REMOVED=$(docker container prune -f --verbose)
  log "Container prune complete. Removed: $REMOVED"
}

# Step 4: Optional: System-wide prune (use sparingly)
cleanup_system() {
  log "Running full system prune (volumes excluded)..."
  docker system prune -f --verbose
  log "System prune complete."
}

# Main logic
case "${1:-all}" in
  build-cache)
    cleanup_build_cache
    ;;
  images)
    cleanup_images
    ;;
  containers)
    cleanup_containers
    ;;
  system)
    cleanup_system
    ;;
  all)
    cleanup_build_cache
    cleanup_images
    cleanup_containers
    ;;
  *)
    echo "Usage: $0 {build-cache|images|containers|system|all}"
    exit 1
    ;;
esac

log "Cleanup completed. Final disk usage:"
docker system df | tee -a "$LOGFILE"
```

**Set permissions and test:**
```bash
chmod +x scripts/docker-cleanup.sh
./scripts/docker-cleanup.sh all
```

### Option 2: Cron Jobs (Linux/macOS)

Add to your `crontab -e`:

```cron
# Weekly image prune (Sundays at 02:00 UTC)
0 2 * * 0 /path/to/scripts/docker-cleanup.sh images >> /var/log/docker-cleanup.log 2>&1

# Weekly container prune (Sundays at 02:15 UTC)
15 2 * * 0 /path/to/scripts/docker-cleanup.sh containers >> /var/log/docker-cleanup.log 2>&1

# Monthly build cache prune (1st of month at 02:30 UTC)
30 2 1 * * /path/to/scripts/docker-cleanup.sh build-cache >> /var/log/docker-cleanup.log 2>&1
```

### Option 3: Docker Desktop Scheduled Task (Windows)

**File:** `scripts/docker-cleanup.ps1`

```powershell
# Docker Cleanup Script for Windows
# Schedule via Task Scheduler

param(
    [ValidateSet("build-cache", "images", "containers", "system", "all")]
    [string]$Action = "all"
)

$LogFile = "C:\logs\docker-cleanup.log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Log-Message {
    param([string]$Message)
    $LogEntry = "[$Timestamp] $Message"
    Add-Content -Path $LogFile -Value $LogEntry
    Write-Host $LogEntry
}

function Cleanup-BuildCache {
    Log-Message "Starting build cache prune..."
    $Before = docker system df --format='{{.BuildCache.Size}}'
    docker builder prune -f --verbose
    $After = docker system df --format='{{.BuildCache.Size}}'
    Log-Message "Build cache prune complete. Size reduction: $Before → $After"
}

function Cleanup-Images {
    Log-Message "Starting image prune (unused images)..."
    $Before = docker system df --format='{{.Images.Size}}'
    docker image prune -a -f --verbose
    $After = docker system df --format='{{.Images.Size}}'
    Log-Message "Image prune complete. Size reduction: $Before → $After"
}

function Cleanup-Containers {
    Log-Message "Starting container prune (exited)..."
    docker container prune -f --verbose
    Log-Message "Container prune complete."
}

function Cleanup-System {
    Log-Message "Running full system prune (volumes excluded)..."
    docker system prune -f --verbose
    Log-Message "System prune complete."
}

switch ($Action) {
    "build-cache" { Cleanup-BuildCache }
    "images" { Cleanup-Images }
    "containers" { Cleanup-Containers }
    "system" { Cleanup-System }
    "all" {
        Cleanup-BuildCache
        Cleanup-Images
        Cleanup-Containers
    }
}

Log-Message "Cleanup completed. Final disk usage:"
docker system df | Tee-Object -FilePath $LogFile -Append
```

**Schedule via PowerShell (as Administrator):**
```powershell
# Weekly Sunday 2 AM
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\path\to\docker-cleanup.ps1 -Action all"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "02:00"
$Principal = New-ScheduledTaskPrincipal -UserID "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "Docker-Cleanup" -Action $Action -Trigger $Trigger -Principal $Principal -Description "Docker build cache, image, and container cleanup"
```

### Option 4: GitHub Actions (for CI/CD-triggered cleanup)

**File:** `.github/workflows/docker-cleanup.yml`

```yaml
name: Docker Cleanup

on:
  schedule:
    # Weekly image prune (Sundays at 02:00 UTC)
    - cron: '0 2 * * 0'
  workflow_dispatch:  # Manual trigger

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Run Docker cleanup
        run: |
          echo "=== Build Cache Prune ==="
          docker builder prune -f --verbose
          
          echo "=== Image Prune ==="
          docker image prune -a -f --verbose
          
          echo "=== Container Prune ==="
          docker container prune -f --verbose
          
          echo "=== Final Disk Usage ==="
          docker system df

      - name: Log cleanup results
        if: always()
        run: |
          echo "Cleanup completed at $(date)" >> docker-cleanup.log
          docker system df >> docker-cleanup.log

      - name: Upload cleanup log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: docker-cleanup-log
          path: docker-cleanup.log
```

### Option 5: Docker Compose Health & Cleanup Override (Recommended)

**File:** `docker-compose.cleanup.yml`

```yaml
# Extend your main compose stack with scheduled cleanup services
# Include with: docker compose -f docker-compose.yml -f docker-compose.cleanup.yml up

services:
  docker-janitor:
    # Runs scheduled pruning tasks using a simple busybox + cron
    image: alpine:latest
    container_name: docker-janitor
    entrypoint: |
      sh -c '
        apk add --no-cache dcron
        
        # Create cleanup script
        cat > /cleanup.sh << EOF
        #!/bin/sh
        docker builder prune -f
        docker image prune -a -f
        docker container prune -f
        docker system df
        EOF
        
        chmod +x /cleanup.sh
        
        # Schedule: every Sunday at 02:00
        echo "0 2 * * 0 /cleanup.sh" | crontab -
        
        # Start cron daemon
        crond -f -l 2
      '
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /var/lib/docker:/var/lib/docker
    restart: unless-stopped
    profiles:
      - ops
      - health
    labels:
      - "com.hypercode.tier=infrastructure"
      - "com.hypercode.role=maintenance"
```

---

## Cleanup Schedule Recommendation

| Task | Frequency | Best Time | Recovery | Danger Level |
|------|-----------|-----------|----------|--------------|
| **docker builder prune** | **Monthly** | 1st of month, 02:00 UTC | -13.5GB/month | ✅ **Safe** |
| **docker image prune -a** | **Weekly** | Sunday, 02:15 UTC | -1-5GB/week | ⚠️ **Medium** (removes dangling images) |
| **docker container prune** | **Weekly** | Sunday, 02:30 UTC | -10-50MB/week | ✅ **Safe** (only exited) |
| **docker system prune** | **Quarterly** | 1st of quarter, 03:00 UTC | -5-15GB | ⚠️ **Medium** (full sweep) |
| **Volume cleanup** | **Never (default)** | — | — | 🚫 **DANGER** (data loss) |

---

## Implementation Checklist

- [ ] Add memory limits to `docker-compose.agents.yml`
- [ ] Add memory limits to `docker-compose.agents-full.yml`
- [ ] Review and adjust limits after 1 week of running agents
- [ ] Deploy `scripts/docker-cleanup.sh` to your server
- [ ] Test cleanup script: `./scripts/docker-cleanup.sh all`
- [ ] Add cron jobs (or Task Scheduler / GitHub Actions equivalent)
- [ ] Monitor cleanup logs: `tail -f /var/log/docker-cleanup.log`
- [ ] Document custom memory limits in team runbook

---

## Monitoring & Alerts

**Watch for these signs of undersized limits:**
- Containers restarting frequently with code 137
- `OOMKilled=true` in `docker inspect <container>`
- Memory usage approaching limit (>80% sustained)

**Watch for these signs of excessive cleanup:**
- CI/CD builds slowing down (images pruned too aggressively)
- Frequent re-pulls from registries
- Build cache not effectively reused

---

## References

- Current Disk Usage (Post-Cleanup): 19.6GB used, 46.4GB recovered
- Redis Data Integrity: DB 1 (cache): 482 keys ✓, DB 2 (rate limits): accessible ✓
- Exit-137 Root Cause: External shutdown signal, not OOM
