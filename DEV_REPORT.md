# HyperCode V2.4 Developer Report

**Audience:** Developers, maintainers, DevOps engineers, QA engineers, and future contributors  
**Project:** HyperCode V2.4  
**Repository:** `welshDog/HyperCode-V2.4`  
**Assessment basis:** Repository inspection and verified local checks  
**Current verified status:** Core development path is operational; full-stack certification remains open

---

## 1. Executive summary

HyperCode V2.4 is a Docker-based AI-agent platform built around a Python FastAPI backend, a multi-service Compose deployment, an agent fleet, asynchronous workers, persistent data services, and optional observability services.

The platform is designed to let agents plan work, dispatch tasks, verify results, enforce safety controls, persist state, recover interrupted runs, and expose operational status through APIs and dashboards.

The repository is active and capable, but it contains several generations of dependency manifests, historical reports, multiple Compose overlays, and a large number of auxiliary agents and experiments. Developers should treat the backend core path and the root Compose entrypoint as the primary system, and should avoid assuming that every historical status document describes the current runtime.

### Current verified results

| Area | Status | Evidence |
|---|---|---|
| Dependency authority | PASS | `.github/scripts/check_dependency_authority.py` |
| Core dependency chain | PASS | `requirements.core.in` → `requirements.core.txt` → `backend/Dockerfile` |
| Python target | PASS | Python 3.12 in backend Dockerfile and CI |
| Crew pause tests | PASS | Included in 82-test focused suite |
| Crew scribe tests | PASS | Included in 82-test focused suite |
| Focused crew suite | PASS | 82 passed, one dependency warning |
| Python compilation | PASS | Backend and scripts compilation checks |
| Compose validation | PASS | Root Compose configuration |
| Observability Compose validation | PASS | Root Compose with `observability` profile |
| Full repository test suite | OPEN | Previous run timed out or was resource-constrained |
| Full Ruff quality gate | OPEN | Large existing issue set remains |
| Observability runtime | OPEN | Several historical stopped containers and exit 137 records |
| Governor service | OPEN | Previous secret file mount mismatch |

---

## 2. What the project does

HyperCode combines an API platform and an agent operating environment.

### Primary capabilities

- Expose a FastAPI API for memory, tasks, users, agents, health, missions, and operator actions.
- Run declarative HyperFlow workflows as persisted graph executions.
- Pause, resume, cancel, and recover workflow runs.
- Dispatch approved crew stages to allow-listed agents.
- Gate sensitive operations through safety and governance checks.
- Store application state in PostgreSQL.
- Use Redis for cache, coordination, queue, and event-related workloads.
- Run Celery workers for asynchronous jobs.
- Provide dashboards and operational views.
- Integrate vector memory through Chroma.
- Integrate object storage through MinIO.
- Provide optional Prometheus, Grafana, Loki, Tempo, and related monitoring services.

The architecture is not a single application. It is a collection of services that are coordinated through Docker Compose, internal networks, HTTP APIs, Redis, PostgreSQL, and workflow state.

---

## 3. Repository layout

| Path | Responsibility |
|---|---|
| `backend/` | Main FastAPI application, models, workflows, tests, migrations, and runtime image |
| `backend/app/` | Python application package |
| `backend/app/api/` | API routers and endpoint modules |
| `backend/app/agents/` | Agent abstractions and HyperFlow execution |
| `backend/app/crew/` | Crew planning, dispatch, governance, evidence, pause, and scribe logic |
| `backend/app/broski_operator/` | Operator run control and recovery functionality |
| `backend/app/core/` | Configuration, security, storage, model routes, memory, and telemetry |
| `backend/app/models/` | SQLAlchemy and domain models |
| `backend/app/services/` | Business services and integrations |
| `backend/alembic/` | Database migration environment and revisions |
| `backend/tests/` | Backend unit, integration, workflow, API, and security tests |
| `agents/` | Specialized AI agents and their Dockerfiles |
| `services/` | Supporting services such as SkillWeaver, MCP, and health components |
| `dashboard/` | Dashboard-related application content |
| `monitoring/` | Prometheus, Grafana, Loki, Tempo, Alertmanager, and agent configurations |
| `scripts/` | Setup, validation, scanning, health, deployment, and operational scripts |
| `.github/` | CI workflows and repository validation scripts |
| `k8s/` | Kubernetes manifests and tests for a future or alternate deployment path |
| `docker-compose.yml` | Root Compose entrypoint using included Compose files |
| `Makefile` | Developer shortcuts for build, test, health, scanning, and stack operations |
| `reports/` | Generated scan and health outputs |
| `docs/` | Project documentation, historical reports, runbooks, and architecture material |

The repository also contains archives, experiments, generated artifacts, historical handovers, and auxiliary projects. Confirm the owning Compose file or build context before modifying a service outside `backend/`.

---

## 4. Backend architecture

### API layer

The backend is a Python 3.12 FastAPI application. API routers live under `backend/app/api/` and are assembled by the application entrypoint.

Typical API areas include:

- Health and readiness checks.
- Authentication and user management.
- Tasks and projects.
- Agent status and orchestration.
- Memory and RAG operations.
- HyperFlow operator tasks.
- Missions and governance.
- Stripe and payment integrations.
- WebSocket uplink functionality.

### HyperFlow execution

`backend/app/agents/hyperflow_runner.py` executes declarative flow definitions.

The runner is responsible for:

- Walking nodes and edges.
- Executing tool and agent-dispatch nodes.
- Waiting at human approval gates.
- Applying retry, fallback, and routing rules.
- Persisting run state.
- Publishing run events.
- Supporting cancellation.
- Supporting durable pause and resume behavior.
- Recovering runs after a process restart.

Flow definitions are represented by schemas and registered through the HyperFlow registry. Workflow tests deliberately verify fail-closed behavior, approval gates, dispatch restrictions, evidence handling, and recovery behavior.

### Crew system

The crew subsystem is a guarded execution path rather than a general-purpose autonomous shell.

The normal conceptual sequence is:

1. Receive a bounded goal.
2. Produce a deterministic plan.
3. Require human approval where configured.
4. Seal the approved plan with a hash.
5. Dispatch a builder stage.
6. Dispatch a verifier stage.
7. Evaluate evidence through the guard.
8. Optionally create a scribe proposal.
9. Require separate approval for documentation publication.
10. Settle eligible rewards only after proof and governance checks.

The crew code intentionally prevents direct arbitrary writes, uncontrolled agent dispatch, secret leakage, and unverified success states.

### Data layer

The platform uses PostgreSQL for durable application and workflow state. Redis is used for cache, queue, coordination, and ephemeral event-related operations. Chroma supports vector memory. MinIO provides S3-compatible object storage.

Alembic migrations are under `backend/alembic/versions/`. Database changes must be accompanied by migration review and relevant model or API tests.

---

## 5. Docker and Compose architecture

The root `docker-compose.yml` is intentionally small. It uses Compose `include` entries to assemble the full system from multiple files.

Important included layers include:

- Core services.
- Observability services.
- Agent services.
- Registry services.
- Obsidian synchronization.
- BROskiPets integration.
- Brain integration.
- Grafana Cloud integration.
- FCC proxy services.
- Throttle and resource-management services.

### Compose profiles

The deployment uses profiles to control resource-heavy or optional groups.

Common profile concepts include:

- Core services that are part of the default runtime.
- `agents` for the agent fleet.
- `observability` for Prometheus, Grafana, Loki, Tempo, and related tools.
- `grafana-cloud` for remote-write and cloud shipping.
- Additional feature profiles for brain, pets, vault synchronization, and related integrations.

Do not start every profile on a memory-constrained workstation. Use the smallest profile that supports the task.

### Backend Dockerfile

`backend/Dockerfile` has two dependency variants:

- `full` installs `backend/requirements.txt`.
- `core` installs `backend/requirements.core.txt`.

The Dockerfile uses Python 3.12 slim images, multi-stage dependency installation, cached dependency layers, a non-root runtime user, health checks, and optional precompiled bytecode.

The core dependency authority chain is:

```text
backend/requirements.core.in
        ↓ compiled lock
backend/requirements.core.txt
        ↓ installed by
backend/Dockerfile core stage
```

The repository checker enforces this relationship:

```powershell
python .github/scripts/check_dependency_authority.py
```

---

## 6. Dependency management

The repository contains multiple dependency descriptions. They do not all describe the same environment.

### Current authority for the core runtime

Use these files for the slim backend runtime:

- `backend/requirements.core.in` for direct package intent.
- `backend/requirements.core.txt` for compiled package resolution.
- `backend/Dockerfile` for the Docker installation path.

The core checker currently reports 41 direct core packages and passes.

### Other dependency files

These files have different purposes or historical states:

- `backend/requirements.txt` describes a broader backend environment.
- `backend/requirements-dev.txt` describes development tooling.
- `backend/requirements-ai.txt` describes optional AI dependencies.
- `backend/requirements-UPGRADED.txt` is an upgrade proposal or alternate set, not the active authority.
- Root `requirements.txt` and `requirements.lock` describe a separate broad environment and should not be assumed to represent the backend image.
- `backend/pyproject.toml` declares project metadata and another dependency set, but the backend Dockerfile does not install from it.

Do not update several manifest families independently. Choose the intended runtime variant first, update its source input, regenerate its compiled output, run the authority checker, and then run the tests.

---

## 7. CI workflow

The main workflow is `.github/workflows/ci.yml`.

The current quality job:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Caches against `backend/requirements.core.txt`.
4. Runs the dependency-authority checker.
5. Installs the backend core requirements and development requirements.
6. Installs additional CI tools.
7. Runs Black checks.
8. Runs the selected Flake8 checks.
9. Runs Bandit.
10. Runs backend pytest.
11. Runs smoke framework coverage checks.
12. Runs available frontend tests.
13. Runs available Playwright tests.

The Docker job builds backend and dashboard images and runs Trivy scans for high and critical vulnerabilities.

### Important CI limitation

The workflow still contains broad quality gates that may not match the repository’s current full lint state. The dependency authority and focused backend tests are verified locally, but the entire CI pipeline has not been established as green by this assessment.

---

## 8. Developer setup

### Recommended environment

- Windows, Linux, or macOS host.
- Docker Desktop or Docker Engine with Compose support.
- Python 3.12 for backend development.
- Node.js 20 for dashboard work.
- Git.
- Sufficient Docker/WSL memory for the selected services.

### Initial configuration

```powershell
Copy-Item .env.example .env
python scripts/validate_env.py
```

Do not commit `.env`, tokens, passwords, private keys, or local secret files.

### Validate dependency authority

```powershell
python .github/scripts/check_dependency_authority.py
```

### Validate Compose

```powershell
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml --profile observability config --quiet
```

### Run the core stack

Use the project’s documented Compose entrypoint and select only the required profiles. When bringing up a Compose application, prefer:

```powershell
docker compose up --pull always -d
```

For development, inspect the relevant Compose file and profile before starting agents or observability.

### Run backend tests

```powershell
pytest backend/tests -q
```

For the verified crew subset:

```powershell
pytest backend/tests/test_crew_pause.py backend/tests/test_crew_scribe.py -q --tb=short
```

### Run compilation checks

```powershell
python -m compileall -q backend/app backend/tests scripts
```

### Run the scoped health scan

```powershell
python scripts/health_report.py --json --target backend --target scripts
```

The scan supports repeatable `--target` values. Avoid repository-wide scans when you only need a subsystem result.

---

## 9. Current runtime status

The local Docker environment has a substantial running stack, including core APIs, databases, queues, agent services, and supporting integrations.

Previously verified healthy or operational services include:

- `hypercode-core`
- PostgreSQL
- Redis
- Chroma
- MinIO
- Celery worker
- Crew Orchestrator
- Healer agent
- Safety Shepherd
- Dashboard
- HyperHealth API and worker
- MCP server
- Agent registry
- SkillWeaver
- FCC proxy
- Throttle agent
- Brain and synchronization services

### Known runtime issues

#### Governor

Governor previously exited because Docker attempted to mount a secret path as the wrong filesystem type. Treat this as a deployment configuration issue. Repair only the Governor service after the host resource guard is safe.

#### Observability

Several observability containers have historical stopped states, including exit code 137 records. The Compose configuration defines resource limits, but starting the entire observability profile can still exceed workstation capacity.

Start observability in stages after confirming available memory:

1. Prometheus.
2. Alertmanager.
3. Grafana.
4. Loki.
5. Tempo.
6. Supporting exporters and collectors.

Always inspect logs after starting a problematic service.

#### Host resource pressure

Earlier full-stack checks reached a RED WSL memory state. Full builds, browser tests, and broad profile restarts should wait until the resource guard reports a safe state.

---

## 10. Test and quality status

### Verified

- 82 crew pause and scribe tests pass.
- Dependency authority check passes.
- Python compilation passes for the checked backend and script paths.
- Root Compose validation passes.
- Observability profile Compose validation passes.
- The two previously failing crew tests are fixed:
  - Safety Shepherd network calls are disabled for deterministic pause unit tests.
  - UTF-8 encoding is explicit for the Windows scribe fixture.

### Open

- Full backend suite has not been certified end-to-end on the current workstation.
- Full Playwright suite has previously exceeded local time limits.
- Ruff reports a large existing issue set across the repository.
- Dependency environments outside the core authority chain remain inconsistent.
- Observability runtime recovery remains incomplete.
- Governor recovery remains incomplete.

### Warning observed

The focused tests emit a `python_multipart` deprecation warning from the installed Starlette environment. It does not currently fail the tests, but it should be tracked during the next dependency refresh.

---

## 11. Development rules

### Before changing backend code

- Read the relevant endpoint, service, model, and test files.
- Check whether the code participates in a workflow or governance path.
- Preserve redaction and fail-closed behavior.
- Add or update tests before changing behavior where practical.
- Run the smallest relevant test subset first.

### Before changing Compose

- Read the root Compose file and all included files that define the service.
- Validate the merged model with `docker compose config --quiet`.
- Check networks, profiles, health checks, secrets, volumes, and resource limits.
- Do not pass an included Compose file again with `-f` if the root file already includes it.
- Avoid full-stack restarts on a memory-constrained host.

### Before changing dependencies

- Identify whether the change is for full runtime, core runtime, development, AI, or an agent-specific image.
- Change the direct source file first.
- Regenerate the compiled file rather than hand-editing it.
- Run the dependency authority checker.
- Run import, compilation, and focused tests.
- Check the Docker build context and installation stage.

### Before changing security or governance code

- Preserve authentication boundaries.
- Do not expose secrets in logs, test output, reports, or API responses.
- Do not weaken approval, evidence, redaction, pause, or guard behavior to make tests pass.
- Add negative tests for bypass attempts.

---

## 12. Recommended next work

### Priority 0: Keep the development path trustworthy

- Keep the dependency authority check in CI.
- Make the backend core test path the primary local developer path.
- Separate current status from historical reports.
- Keep Python 3.12 consistent across Docker and CI.

### Priority 1: Finish runtime recovery

- Repair the Governor secret mount.
- Confirm the host memory guard is safe.
- Restore observability services one at a time.
- Capture current service logs and health results.
- Recheck dashboard latency after resource recovery.

### Priority 1: Establish a complete test matrix

Run in stages:

1. Backend unit tests.
2. Backend integration tests.
3. Agent tests.
4. Worker and queue tests.
5. Dashboard unit tests.
6. Browser tests.
7. Compose health checks.
8. Optional observability checks.

Record passed, skipped, timed-out, and resource-aborted groups separately.

### Priority 2: Reduce quality debt safely

- Scope Ruff by subsystem.
- Fix import ordering and unused imports first.
- Replace bare exception handlers with specific exceptions.
- Add CI gates only after the relevant subsystem is clean.
- Run tests after each batch.
- Avoid repository-wide autofixes without reviewing the complete diff.

### Priority 2: Consolidate dependency metadata

- Keep `requirements.core.in` and `requirements.core.txt` authoritative for the slim backend image.
- Decide whether `backend/pyproject.toml` should become the package authority or remain metadata-only.
- Mark alternate requirement files clearly as development, AI, agent, or historical sets.
- Remove contradictory CI installation paths.

---

## 13. Quick reference commands

```powershell
# Dependency authority
python .github/scripts/check_dependency_authority.py

# Compose validation
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml --profile observability config --quiet

# Core tests
pytest backend/tests -q

# Verified crew subset
pytest backend/tests/test_crew_pause.py backend/tests/test_crew_scribe.py -q --tb=short

# Compile Python
python -m compileall -q backend/app backend/tests scripts

# Scoped health scan
python scripts/health_report.py --json --target backend --target scripts

# Container status
docker compose ps -a

docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs for a problematic service
docker logs <container-name> --tail 200
```

---

## 14. Final developer assessment

HyperCode V2.4 has a substantial and capable development platform with a functioning backend core, guarded workflow execution, persistent state, Docker orchestration, agent services, and a growing test suite.

The safest development path is currently the Python 3.12 backend core with the `requirements.core.in` → `requirements.core.txt` → Dockerfile chain, validated by the dependency-authority checker and the focused crew test suite.

The project should not yet be described as fully certified across every service, browser flow, observability component, and historical agent image. Developers should use current command output rather than older status badges or archived reports when deciding whether a subsystem is production-ready.

The next milestone is a staged green-state validation of the full backend suite, Governor recovery, observability recovery, dashboard latency, and the remaining dependency and lint debt.
