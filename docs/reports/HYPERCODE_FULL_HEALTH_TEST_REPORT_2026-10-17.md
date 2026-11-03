# HyperCode V2.4 Full Health and Test Report

**Assessment date:** 17 October 2026  
**Project:** HyperCode V2.4  
**Compose project:** `hypercode-v24`  
**Host:** Windows Docker Desktop with Linux containers and WSL2  
**Run type:** Full health/test attempt with safety abort

---

## Executive result

A complete full-stack test run was **not safe to complete** because the host RAM guard reached `RED` during the run. The guard reported WSL available memory at approximately **1,004 MB**, below the project’s hard stop threshold of **1,200 MB**. Continuing with the complete dashboard suite, full agent tests, image builds, or broad restart operations would risk another WSL/Docker stall.

The run therefore used a fail-safe approach:

- It inspected the full Compose runtime.
- It ran workflow and Compose validation.
- It collected service health and failure logs.
- It checked the RAM-guard and backup state.
- It performed lightweight endpoint probes.
- It did not continue heavy test suites after the RED signal appeared.

### Overall status

| Area | Result |
|---|---|
| Core API | Healthy, `/health` returned HTTP 200 |
| Databases and storage | Running and healthy in Compose status |
| Celery worker | Running and healthy |
| Dashboard | Running but lightweight API probe timed out under pressure |
| MCP server | Running and healthy in Compose status |
| FCC proxy | Running and internally healthy; unauthenticated probe correctly returned 401 |
| Throttle-agent | Running and healthy |
| Governor | Failed to start, exit code 127, secret mount type mismatch |
| RAM safety | RED; WSL available memory approximately 1,004 MB |
| Workflow YAML | Validated successfully |
| Compose configuration | Validated successfully |
| Focused tests | Not rerun in this pass because host reached RED |
| Full test suite | Safely aborted before completion |
| Off-site backup | One encrypted archive queued while Google Drive is unavailable |

---

## 1. Safety gate outcome

The RAM guard reported:

- Host free memory: approximately 644 MB.
- WSL available memory: approximately 1,004 MB.
- WSL total memory: approximately 3.9 GB.
- WSL swap used: approximately 143 MB.
- Overall verdict: `RED`.
- Project RED threshold: WSL available memory below 1,200 MB.

The largest observed host-side processes included:

- `vmmemWSL`
- `pyrefly`
- multiple `Trae` processes
- Windows Defender process activity

The correct response is to stop heavy Windows applications and wait for the signal to recover before running builds or broad tests.

### Required recovery gate

Do not build, restart the entire stack, or run the dashboard/full-agent test suites until this command reports GREEN:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\ram-guard-task.ps1 -Action status
```

If the guard task is stale again, restart it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\ram-guard-task.ps1 -Action start
```

---

## 2. Runtime inventory

### Running healthy or operational services

The Compose snapshot showed these primary services running:

- PostgreSQL
- Redis
- Chroma
- MinIO
- Memstream
- `hypercode-ollama`
- `hypercode-core`
- Celery worker
- dashboard
- MCP server
- HyperHealth API
- HyperHealth worker
- BROski Pets bridge
- healer-agent
- safety-shepherd
- crew-orchestrator
- agent registry
- coder-agent
- coder-studio
- QA engineer
- skillweaver
- FCC proxy
- throttle-agent
- brain and synchronization services

### Failed service

`governor` exited with code `127`.

The Docker state error identifies the cause:

```text
failed to create shim task ... error mounting ... secrets/agent_api_key_governor.txt ... not a directory: Are you trying to mount a directory onto a file (or vice-versa)?
```

This means the host path is still being treated as a directory by Docker’s active container configuration or the container was created before the directory was replaced. A file check on the host showed the path as a file, so Governor requires a clean container recreation after the host path and Compose secret definition are aligned.

Do not recreate Governor while the RAM guard is RED. After the host returns GREEN, use a targeted recreation rather than restarting the whole project.

### Historical stopped observability services

The following services remain stopped or have historical OOM records:

- Prometheus
- Prometheus Cloud
- Loki
- Tempo
- Grafana
- Grafana Agent
- Pyroscope
- Promtail
- cAdvisor
- node-exporter
- Alertmanager
- Celery exporter

Do not start all of them on this host until a resource budget and GREEN guard signal are present.

---

## 3. Lightweight endpoint checks

The following probes were attempted:

| Endpoint | Result |
|---|---|
| `http://127.0.0.1:8000/health` | HTTP 200 |
| `http://127.0.0.1:8014/health` | HTTP 200 |
| `http://127.0.0.1:8083/v1/models` | HTTP 401, expected without FCC bearer authentication |
| `http://127.0.0.1:8088/api/health` | Timed out after 5 seconds under RED WSL pressure |

The FCC 401 is not a service failure. Its internal healthcheck uses the configured bearer token and had been healthy in the container status.

The dashboard timeout is a performance warning under current resource pressure. It does not prove an application defect by itself. Recheck it after the host returns GREEN.

---

## 4. Validation results

### Compose

The merged Compose model validated successfully before the RED condition was observed:

```text
compose-valid
```

### Workflow YAML

The duplicate-key validator passed:

```text
workflow-yaml-valid
```

### Focused tests

The previously completed focused test run passed:

- RAM-guard tests: 24 passed.
- JWT rotation tests: 13 passed.
- Combined focused tests: 37 passed.

The focused tests were not repeated during the RED-state full-test attempt because running more tests would add load to a host below the WSL safety floor.

### Full tests

The full project test suite was **not completed**. This is intentional and should be recorded as an environment safety abort, not a test failure.

Tests still requiring a GREEN-state run include:

- full backend pytest suite
- dashboard test suite
- throttle-agent full test suite
- economy consumer tests
- agent integration tests
- browser/E2E tests
- full health-check controller
- optional observability checks

---

## 5. Backup status

### Working

- PostgreSQL backup generation is working.
- Redis, MinIO, and Chroma store backups are working.
- Checksums are generated and verified.
- Encrypted archives are generated and tested.
- Second-disk copies are verified.

### Open issue

The latest encrypted archive remains queued because Google Drive for Desktop was not mounted or signed in:

```text
WAITING: Google Drive folder not found
```

Current queued archive count: one.

The latest off-site task status was exit code `0x2`, meaning the archive was created successfully but delivery is waiting for the cloud folder.

Start or sign in to Google Drive for Desktop, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\backup-offsite-task.ps1 -Action start
```

Verify delivery:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\backup-offsite-task.ps1 -Action status
```

---

## 6. Governor recovery plan

The current Governor failure is a deployment integrity issue, not an application logic failure.

After the RAM guard returns GREEN:

1. Stop only the failed Governor container.
2. Verify both host paths are files, not directories.
3. Verify both files are non-empty.
4. Validate the secrets overlay.
5. Recreate only Governor.
6. Wait for its healthcheck.
7. Test agent authentication.
8. Test operator approval routes without exposing the key.

Suggested targeted commands:

```powershell
Get-Item .\secrets\agent_api_key_governor.txt, .\secrets\governor_operator_key.txt |
  Select-Object Name, PSIsContainer, Length

docker compose -f docker-compose.yml -f docker-compose.secrets.yml config --quiet

docker compose up -d --force-recreate governor

docker inspect governor --format '{{json .State.Health}}'
```

If Docker still reports a directory-to-file mount mismatch after the host paths are confirmed as files, remove and recreate only the Governor container, not its volumes or the full application stack.

---

## 7. Findings by priority

### P0: Stop heavy operations until RAM is GREEN

This is the immediate blocker. The stack is operating with WSL below the project’s RED threshold.

Actions:

- Close Trae, Pyrefly, and other heavy Windows processes.
- Avoid builds.
- Avoid full Compose restart.
- Avoid full dashboard/browser suites.
- Avoid enabling observability.
- Wait for a fresh GREEN signal.

### P0: Recover Governor after the resource gate clears

Governor cannot start because Docker is attempting to mount a directory as a file. This must be corrected before relying on governance approval functions.

### P1: Recheck dashboard after memory recovery

The dashboard API health probe timed out while Core and other services remained healthy. Recheck `/api/health`, `/api/metrics`, `/api/fleet`, and `/api/safety` after the host returns GREEN.

### P1: Complete Google Drive delivery

The local and encrypted backup pipeline works, but one archive has not reached the off-site destination.

### P1: Run the full tests in stages

Do not run everything concurrently on this workstation. Use this order:

1. backend unit tests
2. throttle-agent tests
3. economy tests
4. dashboard unit tests
5. dashboard browser tests
6. agent integration tests
7. full health check
8. optional observability checks

Use a fresh RAM-guard check between stages.

### P2: Investigate historical observability failures

The observability containers have historical exit code 137 records. Run them individually in a GREEN state, starting with Prometheus and Grafana, then add Loki and Tempo only if memory remains stable.

---

## 8. Safe next-run procedure

### Step 1: recover host resources

Close heavy applications and wait for:

- WSL available memory at least 1.5 GB for test work.
- Preferably WSL available memory above 2 GB for browser tests.
- Fresh RAM signal.
- No RED state.

### Step 2: verify base services

```powershell
docker compose ps -a
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8014/health
```

### Step 3: repair Governor only

Use the targeted recovery commands above. Do not recreate the complete stack.

### Step 4: run staged tests

```powershell
python -m pytest backend -q --disable-warnings --maxfail=1
python -m pytest agents/throttle-agent -q --disable-warnings --maxfail=1
python -m pytest scripts -q --disable-warnings --maxfail=1
```

Run dashboard tests separately after confirming the RAM guard remains GREEN.

### Step 5: run the full health checker last

The health checker itself creates load. Run it after the application and focused tests are complete, not before.

### Step 6: generate a final green-state report

The final report should distinguish:

- passed tests
- skipped tests
- environment-aborted tests
- service failures
- historical stopped containers
- deliberate profile-disabled services

---

## 9. Final assessment

The platform itself remains largely functional: Core is healthy, the databases and storage services are healthy, Celery is healthy, FCC and throttle-agent are healthy, and the workflow/Compose validation layer is healthy.

This run did not establish full test-suite success because the host crossed the RED memory threshold. The correct outcome was to stop rather than push the workstation into another WSL/Docker stall.

The immediate success criteria are:

1. Recover WSL memory above the GREEN test floor.
2. Recreate Governor successfully with file-mounted secrets.
3. Confirm dashboard endpoints recover from the timeout.
4. Deliver the queued encrypted backup to Google Drive.
5. Run the complete test suite in staged batches.
6. Enable observability only after the default stack remains stable.

Until those conditions are met, treat the project as **functionally healthy but not fully test-certified on the current host**.
