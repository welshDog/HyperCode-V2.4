# Grafana 2026 Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade your self-hosted observability stack (Grafana + Loki + optional Pyroscope + k6 workflow) in a safe, reversible way, and map “Grafana 2026 features” to what you already run.

**Architecture:** You already run Grafana/Prometheus/Loki/Tempo via Docker Compose with provisioning in `monitoring/grafana/provisioning`. We’ll (1) take backups, (2) pin + upgrade image tags, (3) verify health + dashboards, (4) optionally add Pyroscope and a k6 load-test workflow.

**Tech Stack:** Docker Compose, Grafana, Prometheus, Loki, Tempo, Promtail, (optional) Pyroscope, (optional) k6.

**Status (2026-05-31):**
- Task 1 complete (backups captured)
- Task 2 complete (Grafana upgraded to 13.0.1)
- Task 3 complete (Loki/Promtail upgraded to 3.5.7)
- Monitoring coverage expanded (Prometheus scrapes + dashboards + alerts)

---

## Current State (known from repo)

- Primary stacks:
  - `docker-compose.core.yml` + `docker-compose.observability.yml` (Grafana on `:3001`, Loki on `:3100`, Tempo on `:3200`)
  - `docker-compose.monitoring.yml` (smaller monitoring set)
- Current pins (defaults in compose):
  - Grafana: `grafana/grafana:11.2.0`
  - Loki: `grafana/loki:3.1.0`
  - Promtail: `grafana/promtail:3.1.0`
- Dashboards-as-code is effectively already in place:
  - Dashboards JSON committed under `monitoring/grafana/provisioning/dashboards/`
  - Provisioning provider: `monitoring/grafana/provisioning/dashboards/dashboard.yml`

---

### Task 1: Preflight snapshot + rollback backups

**Files:**
- No code changes

- [ ] **Step 1: Confirm which compose file actually owns Grafana**

Run (PowerShell, from repo root). This tells you which stack contains the `grafana` service:
```powershell
cd h:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml ps
docker compose -f docker-compose.monitoring.yml ps
docker compose -f docker-compose.yml -f docker-compose.secrets.yml ps
```
Expected:
- One of these commands lists `grafana` (and likely `loki`, `tempo`, etc.) as a service.
- That file (or file pair) is the one you should use for Tasks 2–3.

- [ ] **Step 2: Capture Grafana version + health**

Run:
```powershell
curl.exe -s http://localhost:3001/api/health
```
Expected: JSON containing `"database":"ok"` and `"version":"11.2.0"` (or your current version).

- [ ] **Step 3: Backup Grafana volume**

Run:
```powershell
mkdir artifacts -ErrorAction SilentlyContinue
$grafanaVol = (docker inspect grafana --format "{{range .Mounts}}{{if eq .Destination \"/var/lib/grafana\"}}{{.Name}}{{end}}{{end}}")
docker run --rm -v "$grafanaVol:/var/lib/grafana" -v "$($PWD.Path)\artifacts:/backup" alpine:3.20 sh -lc "tar -czf /backup/grafana-data.tgz -C /var/lib grafana"
```
Expected: `artifacts/grafana-data.tgz` exists.

- [ ] **Step 4: Backup Loki volume (if using observability compose)**

Run:
```powershell
$lokiVol = (docker inspect loki --format "{{range .Mounts}}{{if eq .Destination \"/loki\"}}{{.Name}}{{end}}{{end}}")
docker run --rm -v "$lokiVol:/loki" -v "$($PWD.Path)\artifacts:/backup" alpine:3.20 sh -lc "tar -czf /backup/loki-data.tgz -C / loki"
```
Expected: `artifacts/loki-data.tgz` exists.

- [ ] **Step 5: Commit nothing**

This task is intentionally “no git changes”.

---

### Task 2: Upgrade Grafana safely (pin to v13.0.1)

**Files:**
- Modify:
  - `docker-compose.observability.yml`
  - `docker-compose.monitoring.yml`
- Verify:
  - `http://localhost:3001/api/health`

- [ ] **Step 1: Pin Grafana image to v13.0.1 (avoid `latest`)**

Edit both compose files by changing the Grafana default image:
- From:
  - `grafana/grafana:11.2.0`
- To:
  - `grafana/grafana:13.0.1`

Concrete target lines:
- `docker-compose.observability.yml` → `services.grafana.image`
- `docker-compose.monitoring.yml` → `services.grafana.image`

- [ ] **Step 2: Pull + restart Grafana**

Run (choose the compose file you actually use):
```powershell
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml pull grafana
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml up -d grafana
```

- [ ] **Step 3: Verify Grafana is healthy and on v13**

Run:
```powershell
curl.exe -s http://localhost:3001/api/health
```
Expected: JSON includes `"database":"ok"` and `"version":"13.0.1"`.

- [ ] **Step 4: Verify provisioning still loads dashboards**

Manual check:
- Open `http://localhost:3001`
- Confirm the “Mission Control” folder exists and dashboards render.

- [ ] **Step 5: Commit**

```powershell
git add docker-compose.observability.yml docker-compose.monitoring.yml
git commit -m "chore: upgrade Grafana to 13.0.1"
```

---

### Task 3: Upgrade Loki + Promtail safely (from 3.1.0 → 3.5.7)

**Files:**
- Modify:
  - `docker-compose.observability.yml`
  - `docker-compose.monitoring.yml`
- Verify:
  - `http://localhost:3100/ready`

- [ ] **Step 1: Pin Loki/Promtail images**

Edit both compose files:
- `LOKI_IMAGE` default:
  - From: `grafana/loki:3.1.0`
  - To: `grafana/loki:3.5.7`
- `PROMTAIL_IMAGE` default:
  - From: `grafana/promtail:3.1.0`
  - To: `grafana/promtail:3.5.7`

- [ ] **Step 2: Pull + restart Loki + Promtail**

Run (choose the compose file you actually use):
```powershell
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml pull loki promtail
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml up -d loki promtail
```

- [ ] **Step 3: Verify readiness**

Run:
```powershell
curl.exe -s http://localhost:3100/ready
```
Expected: `ready`

- [ ] **Step 4: Quick Grafana verification**

Manual check:
- Open Explore → Loki datasource
- Run a simple query: `{container="grafana"}`
- Expected: log lines return quickly.

- [ ] **Step 5: Commit**

```powershell
git add docker-compose.observability.yml docker-compose.monitoring.yml
git commit -m "chore: upgrade Loki/Promtail to 3.5.7"
```

---

### Task 4: “Dashboards as Code” workflow (GitOps without extra Grafana features)

**Files:**
- Create:
  - `docs/OBSERVABILITY_DASHBOARDS_AS_CODE.md`
- Modify:
  - `docs/OBSERVABILITY_QUICK_START.md`
- Verify:
  - New dashboards appear via provisioning after restart

- [ ] **Step 1: Document the workflow you already have**

Create `docs/OBSERVABILITY_DASHBOARDS_AS_CODE.md` describing:
- Source of truth: `monitoring/grafana/provisioning/dashboards/*.json`
- Provider config: `monitoring/grafana/provisioning/dashboards/dashboard.yml`
- Workflow: edit in UI → export JSON → overwrite repo file → restart Grafana → commit
- Validation: `python scripts/maintenance/grafana_provisioning_doctor.py`
- Recovery pointer: `docs/grafana_provisioning_recovery.md`

Notes:
- This workflow works even if `github-sync` is unhealthy; `github-sync` only affects “auto-sync to vault/Obsidian”, not Grafana provisioning itself.

- [ ] **Step 2: Verify provisioning refresh works**

Run:
```powershell
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml restart grafana
```
Expected: dashboard set remains intact on reload.

- [ ] **Step 3: Commit**

```powershell
git add docs/OBSERVABILITY_DASHBOARDS_AS_CODE.md docs/OBSERVABILITY_QUICK_START.md
git commit -m "docs: dashboards-as-code workflow"
```

---

### Task 5: Add Pyroscope (optional) for continuous profiling

**Files:**
- Modify:
  - `docker-compose.observability.yml`
  - `monitoring/grafana/provisioning/datasources/datasource.yml`
- Verify:
  - Pyroscope HTTP UI responds
  - Grafana can add Pyroscope datasource

- [ ] **Step 1: Add Pyroscope service to `docker-compose.observability.yml`**

Add under `services:`:
```yaml
  pyroscope:
    image: grafana/pyroscope:2.0.2
    container_name: pyroscope
    command: ["-config.file=/etc/pyroscope/config.yaml"]
    volumes:
      - ./monitoring/pyroscope/config.yaml:/etc/pyroscope/config.yaml
      - pyroscope-data:/data
    ports:
      - "127.0.0.1:4040:4040"
    networks:
      - obs-net
      - agents-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 512M
        reservations:
          cpus: "0.05"
          memory: 128M
```

And add to `volumes:` (same file):
```yaml
  pyroscope-data:
    driver: local
```

- [ ] **Step 2: Add Pyroscope config file**

Create `monitoring/pyroscope/config.yaml`:
```yaml
server:
  http_listen_port: 4040

storage:
  backend: filesystem
  filesystem:
    dir: /data
```

- [ ] **Step 3: Bring Pyroscope up**

Run:
```powershell
docker compose -f docker-compose.observability.yml up -d pyroscope
```

- [ ] **Step 4: Verify Pyroscope is reachable**

Run:
```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:4040/
```
Expected: `200`

- [ ] **Step 5: Add Pyroscope datasource provisioning**

Append to `monitoring/grafana/provisioning/datasources/datasource.yml` under `datasources:`:
```yaml
  - name: Pyroscope
    type: grafana-pyroscope-datasource
    uid: pyroscope
    url: http://pyroscope:4040
    access: proxy
    editable: true
```

- [ ] **Step 6: Restart Grafana and verify datasource exists**

Run:
```powershell
docker compose -f docker-compose.observability.yml restart grafana
```

Manual check:
- Grafana → Connections → Data sources
- Expected: Pyroscope datasource present.

- [ ] **Step 7: Commit**

```powershell
git add docker-compose.observability.yml monitoring/pyroscope/config.yaml monitoring/grafana/provisioning/datasources/datasource.yml
git commit -m "feat: add Pyroscope (profiling) to observability stack"
```

---

### Task 6: Add a k6 load test workflow (optional, keeps cost at 0)

**Files:**
- Create:
  - `tests/load/k6/smoke.js`
  - `tests/load/k6/README.md`
- Verify:
  - Script runs locally and outputs summary

- [ ] **Step 1: Add a minimal k6 script for HyperCode Core**

Create `tests/load/k6/smoke.js`:
```js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '20s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

const baseUrl = __ENV.HYPERCODE_CORE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${baseUrl}/health`);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}
```

- [ ] **Step 2: Document how to run it**

Create `tests/load/k6/README.md`:
```md
# k6 Load Tests

Run with Docker:
docker run --rm -i -e HYPERCODE_CORE_URL=http://host.docker.internal:8000 -v ${PWD}:/work -w /work grafana/k6:0.57.0 run tests/load/k6/smoke.js
```

- [ ] **Step 3: Run it once**

Run (PowerShell):
```powershell
docker run --rm -i `
  -e HYPERCODE_CORE_URL=http://host.docker.internal:8000 `
  -v "$($PWD.Path)":/work `
  -w /work `
  grafana/k6:0.57.0 run tests/load/k6/smoke.js
```
Expected: k6 summary output and exit code 0.

- [ ] **Step 4: Commit**

```powershell
git add tests/load/k6/smoke.js tests/load/k6/README.md
git commit -m "test: add k6 smoke load test for /health"
```

---

## Self-Review (plan quality)

- Coverage:
  - Grafana upgrade ✅
  - Loki/Promtail upgrade ✅
  - Dashboards-as-code workflow ✅
  - Optional Pyroscope ✅
  - Optional k6 ✅
- Placeholder scan:
  - No “TBD” or “later” steps
  - All tasks include concrete file paths and runnable commands

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-30-grafana-2026-upgrades-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks in this session, batch execution with checkpoints

Which approach?

---

## Pre-req (optional, but recommended): Fix `github-sync` health

If you want “dashboards auto-sync to vault” working again, `github-sync` needs a token:

- Compose expects `GITHUB_TOKEN` (not `GITHUB_PAT`) in `docker-compose.agents.yml`.
- Your `.env.example` already includes a `GITHUB_TOKEN=` line.

Minimal fix path:
1) Set `GITHUB_TOKEN` (classic PAT or fine-grained PAT) in your local `.env`/secrets workflow
2) Restart the `github-sync` container
