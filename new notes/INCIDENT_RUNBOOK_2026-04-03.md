# HyperCode V2.0 — Incident Runbook (P0/P1)
**Target environment**: Windows + WSL2 (Docker Desktop)  
**Primary incident**: 9 agents exited (255), celery-worker memory pressure, severe Docker disk bloat

---

## 0) Set a Compose command (WSL)

In WSL bash:

```bash
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  DC="docker-compose"
fi
echo "Using: $DC"
```

Run all commands below from the repo root: `HyperCode-V2.0/`

---

## 1) Snapshot current state (2 minutes)

```bash
$DC ps
docker stats --no-stream
docker system df
```

**Look for**:
- any `Exited` / `Restarting`
- celery-worker memory high (approaching its limit)
- `docker system df` showing huge reclaimable images/build cache/volumes

---

## 2) Find the “smoking gun” (5 minutes)

### 2.1 Celery worker logs (most likely root cause)
```bash
$DC logs celery-worker --tail 200
```

### 2.2 One failing agent + the restart-loop agent
```bash
$DC logs backend-specialist --tail 200
$DC logs super-hyper-broski-agent --tail 200
```

### 2.3 Quick dependency pings (Redis/Postgres/Core)
```bash
docker exec redis redis-cli ping
docker exec postgres pg_isready -U postgres || true
curl -fsS http://127.0.0.1:8000/health || true
```

If Redis/Postgres/Core are unhealthy, fix those first (restart them) before restarting agents.

---

## 3) P0 Recovery: bring agents back online (10–15 minutes)

### 3.1 Restart celery-worker first
```bash
$DC restart celery-worker
sleep 5
$DC ps celery-worker
$DC logs celery-worker --tail 50
docker stats --no-stream celery-worker
```

### 3.2 Stagger restart all 9 agents (prevents cascade)
```bash
AGENTS=(
  backend-specialist
  coder-agent
  database-architect
  devops-engineer
  frontend-specialist
  qa-engineer
  security-engineer
  system-architect
  super-hyper-broski-agent
)

for a in "${AGENTS[@]}"; do
  echo "Restarting $a ..."
  $DC restart "$a" || $DC up -d "$a"
  sleep 5
done
```

### 3.3 Verify: no Exited/Restarting
```bash
$DC ps
$DC ps | grep -Ei "exited|restarting" && echo "Still unhealthy" || echo "OK"
```

On Windows PowerShell (optional check):
```powershell
docker compose ps | Select-String -Pattern "Exited|Restarting"
```

---

## 4) P0 Recovery: nuke Docker disk bloat safely (10–20 minutes)

### 4.1 Confirm reclaimable size
```bash
docker system df
```

### 4.2 Cleanup (images/build cache/volumes)
Use the provided script:
```bash
bash healthfix/scripts/disk-cleanup.sh
```

Or run manually:
```bash
docker image prune -a --force --filter "until=24h"
docker builder prune --force --keep-storage=1gb
docker volume prune -f
docker system df
```

**Expected**: reclaim ~50–60GB if your system matches the audit.

---

## 5) P0/P1: apply celery memory tuning + memory limits (10 minutes)

This pack includes an override file you can layer on top of your existing compose:

```bash
$DC -f docker-compose.yml -f healthfix/compose/docker-compose.override.healthfix.yml up -d
```

Then verify:
```bash
docker stats --no-stream celery-worker
```

---

## 6) P1: enable auto-recovery (today)

### 6.1 Run on-demand
```bash
bash healthfix/scripts/restart-failed-agents.sh
```

### 6.2 Schedule every 5 minutes (Windows)
See: `docs/WINDOWS_TASK_SCHEDULER_AUTORECOVERY.md`

---

## 7) P1: enable Prometheus alerting (this week)

- Alert rules file: `monitoring/prometheus/alert_rules_hypercode.yml`
- Wiring guide: `docs/PROMETHEUS_ALERTING_WIRING.md`

