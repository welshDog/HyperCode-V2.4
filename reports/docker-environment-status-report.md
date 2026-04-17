# HyperCode V2.4 — Docker Environment Health Report

Generated: 2026-04-17

## Executive Summary

Overall Status: CRITICAL

Primary blockers:
- Core data services are down (postgres, redis). Multiple dependent containers are failing or restarting.
- Persistent volume bind targets resolve to a host path that does not exist on this Windows filesystem, consistent with data-layer instability.
- Security scanning for hypercode-core via Trivy is timing out, so current vulnerability posture for the largest image is unknown.

## Severity Scale

- CRITICAL: service outage, data risk, or security visibility loss
- HIGH: major degradation, repeated restarts, or broad reliability impact
- MEDIUM: partial degradation or misconfiguration with limited blast radius
- LOW: minor issue, optimization, or hygiene

## System Baselines (Snapshot)

### Docker Engine

- Docker Desktop: 4.69.0
- Engine: 29.4.0 (linux/amd64, WSL2 kernel 6.6.87.2)
- Context: desktop-linux
- Resources: 6 CPUs, 4.803 GiB memory

### Docker Daemon Responsiveness

- docker ps latency: ~249 ms
- docker images latency: ~853 ms
- docker inspect latency: ~299 ms

### Disk Utilization (docker system df)

- Images: 71.82 GB (reclaimable 22.08 GB)
- Build cache: 14.81 GB
- Local volumes: 1.089 GB

Notable large images:
- hypercode-core:latest ~13.9 GB
- hypercode-v24-celery-worker ~13.8 GB

### Resource Utilization (docker stats --no-stream)

Highest memory consumers:
- hypercode-core: ~553.5 MiB / 1.5 GiB (36%)
- hypercode-dashboard: ~72.5 MiB / 512 MiB (14%)
- broski-pets-bridge: ~64.5 MiB / 256 MiB (25%)

Notable CPU spikes:
- celery-exporter: >100% at snapshot
- celery-worker: ~83% at snapshot

## Container Health & Restart Behavior

### CRITICAL

- broski-bot
  - Status: restarting
  - RestartCount: 49
  - Log root cause: missing required database settings (db_password)
- hypercode-core
  - Status: running but failing startup loops
  - RestartCount: 35
  - Log root cause: cannot resolve postgres host; startup fails during DB metadata init
- redis (exited)
  - Symptoms: shutdown errors and persistence write issues
- postgres (exited)
  - Symptoms: repeated broken pipe / client disconnects then shutdown
- minio (exited)
  - Symptoms: read/write quorum failures, indicates storage drives not online
- observability stack (prometheus, grafana, loki, tempo, promtail, alertmanager) are not currently running

### HIGH

- celery-exporter
  - Status: running (health: starting)
  - RestartCount: 123
  - Log root cause: cannot resolve redis:6379 (name resolution failure)
- celery-worker
  - Status: running (health: starting)
  - RestartCount: 73

### OK (Healthy)

- broski-pets-bridge (healthy)
- healer-agent (healthy)
- hypercode-dashboard (healthy)
- hypercode-mcp-server (healthy)
- docker-socket-proxy, docker-socket-proxy-build (healthy)
- node-exporter, cadvisor (healthy)
- agent-x, hyper-architect, hyper-worker, hyper-observer, super-hyper-broski-agent (healthy)

## Network Connectivity

### Findings

- From broski-pets-bridge container (agents-net + data-net):
  - mcp-gateway:8099 reachable
  - hypercode-core:8000 connection refused at test time
  - redis:6379 DNS not resolvable (container is stopped, so DNS entry not present)
  - postgres:5432 DNS not resolvable (container is stopped, so DNS entry not present)

Impact:
- Any service requiring redis/postgres is unstable or down.

## Volume Mount Integrity

### CRITICAL

Multiple Docker volumes are configured as local-driver bind mounts to:
- H:/HyperStation zone/HyperCode/volumes/<service>

On this Windows filesystem, H:\HyperStation zone\HyperCode\volumes does not exist.

Observed symptoms consistent with missing/invalid bind targets:
- redis log indicates failure saving RDB temp file under /data
- minio reports “no online disks found” and quorum failures

## Port Exposure Validation

### HIGH (Public binds on 0.0.0.0)

The following running containers publish ports on all interfaces:
- agent-x: 8080/tcp (0.0.0.0 and [::])
- hyper-architect: 8091/tcp (0.0.0.0 and [::])
- hyper-observer: 8092/tcp (0.0.0.0 and [::])
- hyper-worker: 8093/tcp (0.0.0.0 and [::])

Everything else observed is localhost-bound (127.0.0.1) or internal-only.

## Security Vulnerabilities (Images)

### HIGH (Security visibility gap)

The always-on Trivy scanner container is running, but it is not producing the expected output file:
- Expected: reports/security/trivy-hypercode-core.json
- Current state: missing
- Scanner log shows: context deadline exceeded during analysis of hypercode-core:latest

Impact:
- Current HIGH/CRITICAL vulnerability counts for hypercode-core cannot be confirmed from this environment snapshot.

## Environment Variable Consistency

Compose evaluation reports unset variables (defaulting to blank string):
- API_KEY
- DISCORD_TOKEN
- HYPERCODE_JWT_SECRET
- HYPERCODE_MEMORY_KEY
- MINIO_ROOT_USER
- MINIO_ROOT_PASSWORD

Observed runtime impact:
- broski-bot fails because DB password resolves to blank.

## Remediation Recommendations

### CRITICAL (Do first)

- Fix persistent volume bind targets:
  - Create the missing host directory tree under H:\HyperStation zone\HyperCode\volumes\*
  - Or update HC_DATA_ROOT so it points to an existing, Docker-shared path and recreate the volumes
- Restore data services:
  - Bring up postgres + redis and confirm they become healthy before starting dependent services
- Fix required secrets/env:
  - Ensure POSTGRES_PASSWORD (or DB_PASSWORD) is set so broski-bot can initialize its DB

### HIGH

- Reduce restart storms:
  - celery-exporter and celery-worker should not restart repeatedly; validate redis DNS + broker URL and network attachment
- Restore observability stack:
  - Bring up prometheus/grafana/loki/tempo/promtail/alertmanager to regain metrics/logs/traces
- Close public port binds unless explicitly intended:
  - Consider binding agent ports to 127.0.0.1 or moving them behind a gateway

### MEDIUM

- Trivy stability:
  - Increase Trivy timeout for hypercode-core scans and disable secret scanning for image scans if needed
  - Store the generated JSON under reports/security and track 0 CRITICAL as a release gate

## Next Health Check Run

Re-run these after remediation to confirm improvement:
- docker compose ps
- docker stats --no-stream
- curl http://127.0.0.1:8000/health
- curl http://127.0.0.1:8098/health
- docker logs broski-bot (should show DB init success)

