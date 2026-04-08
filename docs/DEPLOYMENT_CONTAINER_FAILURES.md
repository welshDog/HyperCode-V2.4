# Deployment Container Failures — Findings & Remediation

## Summary

The active Docker Compose project in the environment is `hypercode-v20`. Several containers were in restart loops due to stale host bind-mount paths referencing a removed directory (`HyperCode-V2.0`). A subset of monitoring components also failed due to missing configuration mounts.

## Symptoms Observed

- Multiple services continuously restarting (examples: `broski-bot`, `celery-worker`, `test-agent`, `tips-tricks-writer`, `throttle-agent`, `alertmanager`).
- Core API (`hypercode-core`) was not running, which prevents dependent agents from operating correctly.
- `alertmanager` repeatedly exited with:
  - `open /etc/alertmanager/alertmanager.yml: no such file or directory`

## Root Causes

### 1) Stale bind mounts to missing host paths

Several containers were bind-mounting their application code from:

- `H:\HyperStation zone\HyperCode\HyperCode-V2.0\...`

Because that directory does not exist, Docker created/treated the mount source as empty, which caused runtime failures like:

- `python: can't open file '/app/src/main.py'` (BROski bot)
- `ModuleNotFoundError: No module named 'app'` (Celery worker)

### 2) Monitoring config mount missing for Alertmanager

Alertmanager was started without `/etc/alertmanager/alertmanager.yml` being present in the container, triggering a crash loop.

### 3) Docker socket proxy hardening needed tmpfs

`tecnativa/docker-socket-proxy` was started with `read_only: true` but without writable tmpfs mounts, causing HAProxy pidfile failures:

- `Cannot create pidfile /run/haproxy.pid`

## Remediation Applied

### Service recovery using the v2.4 compose definition

Affected services were recreated using the v2.4 compose file as the project directory so bind mounts resolve to:

- `H:\HyperStation zone\HyperCode\HyperCode-V2.4\...`

An external network overlay was used so the deployment can reuse existing `hypercode_public_net` and `hypercode-v20_hypercode-net` safely.

### Restored core API + dependent agents

`hypercode-core` was brought up and confirmed healthy, then key agents/services were recreated and stabilized.

### Fixed docker-socket-proxy runtime

Added `tmpfs` mounts for `/run` and `/var/lib/haproxy` while keeping the filesystem read-only.

## Monitoring / Alerting

- Prometheus was started (binds `127.0.0.1:9090`) and configured to load docker health alerts from `monitoring/prometheus/docker_alerts.yml`.
- Alertmanager was recreated with its configuration mounted from `monitoring/alertmanager`.

## Validation

- All previously failing containers transitioned from `Restarting` to `Up` and `healthy` (where healthchecks exist).
- Critical runtime mounts now point to `HyperCode-V2.4` paths rather than the missing `HyperCode-V2.0` paths.

## Preventing Recurrence

- Avoid absolute bind mount paths tied to old repo directories; prefer compose project directory relative mounts.
- Keep a single authoritative compose entrypoint for deployments; avoid running “v20” and “v2.4” stacks side-by-side without explicit separation.
- For socket hardening, always pair `read_only: true` with writable `tmpfs` for components that need `/run` (HAProxy, nginx, etc.).
