# HyperCode V2.4 Project Upgrade Report

**Assessment date:** 2026-10-16  
**Project:** HyperCode V2.4 / Compose project `hypercode-v24`  
**Environment:** Docker Desktop on Windows with Linux containers and WSL2 networking  
**Scope:** Application structure, Compose architecture, runtime state, security, reliability, observability, resource control, AI routing, and next-level upgrade planning.

---

## 1. Executive assessment

HyperCode V2.4 is a broad AI-agent platform rather than a single application. It combines a FastAPI core, PostgreSQL, Redis, Celery, a dashboard, a large agent fleet, MCP services, memory/vector services, local model routing, free-LLM proxying, governance services, Discord integrations, object storage, and an optional observability stack.

The project has already moved beyond a basic Compose deployment. It includes service healthchecks, restart policies, internal bridge networks, persistent volumes, Docker socket proxies, agent identity keys, governance controls, RAM-pressure management, a free-LLM proxy, migration history, and extensive operational scripts.

The current architecture is capable but operationally complex. The next level is not adding more services. It is creating a reliable control plane around the existing services: one canonical launch contract, one secret-loading path, pinned image references, deterministic profiles, reproducible builds, tested recovery procedures, and a resource budget enforced by CI and runtime checks.

### Current maturity rating

| Area | Rating | Assessment |
|---|---:|---|
| Application breadth | High | Core, agents, memory, MCP, governance, integrations, and AI routing are present. |
| Local development | High | Compose includes, bind mounts, scripts, and profiles support rapid iteration. |
| Runtime reliability | Medium | Core services run, but several created or historical stopped services remain. |
| Secret management | Medium-low | Secret files exist, but `.env` values still reach application containers. |
| Resource control | Medium-high | Throttle-agent works in observe mode and uses a scoped Docker proxy. |
| Observability | Medium | Extensive configuration exists, but the monitoring profile previously suffered OOM exits. |
| Supply-chain control | Medium-low | Many services use `latest` or mutable local tags. |
| Production readiness | Medium | The platform needs a formal deployment contract and recovery verification. |

---

## 2. What the project contains

### Core runtime

- `hypercode-core` provides the main FastAPI application.
- PostgreSQL stores application state, governance data, identities, missions, payments, pets, and migrations.
- Redis provides queues, caching, Celery transport, agent coordination, and multiple logical databases.
- `celery-worker` processes asynchronous jobs.
- `hypercode-ollama` is a Socat shim to Docker Model Runner’s Ollama-compatible endpoint.
- `memstream` provides memory or local inference support around a mounted model directory.
- `chroma` provides persistent vector storage.
- MinIO provides S3-compatible object storage.

### Agent and orchestration plane

- `crew-orchestrator` coordinates agents.
- `agent-registry` exposes fleet registration and health information.
- `healer-agent` performs service recovery actions through a scoped Docker proxy.
- `safety-shepherd` provides safety and policy checks.
- `governor` manages capability and approval-related controls.
- `coder-agent`, `coder-studio`, `qa-engineer`, `skillweaver`, and brain-oriented services extend the platform.
- The repository contains a larger optional agent fleet in `docker-compose.agents.yml` and `docker-compose.agents-full.yml`.

### AI and integration plane

- `fcc-proxy` exposes the free-LLM routing layer on `127.0.0.1:8083`.
- FCC can route through local Docker Model Runner, NVIDIA NIM, OpenRouter, and optional Gemini configuration.
- MCP services expose tools and agent integration points.
- Discord, GitHub synchronization, Obsidian synchronization, BROski services, and course/payment integrations are present.

### Resource and operations plane

- `throttle-agent` monitors Docker/container resource behavior and host RAM signal files.
- It uses `docker-socket-proxy-healer` rather than a direct Docker socket mount.
- It is currently configured in `observe` mode, which records decisions without pausing containers.
- RAM signals are mounted read-only from `./ram-signal/ram.json`.
- Operational scripts include health checks, backups, Compose validation, secret initialization, cleanup, fleet checks, and deployment helpers.

### Observability plane

The optional `observability` profile contains Prometheus, Grafana, Loki, Tempo, Pyroscope, Promtail, node-exporter, cAdvisor, Alertmanager, and Celery exporter. The project also has Grafana Cloud remote-write configuration.

This is a strong capability set, but it is too large to run continuously on a constrained Docker Desktop machine without a deliberate resource budget.

---

## 3. Current runtime findings

### Healthy and valuable services

The current runtime evidence shows these services running or recently confirmed healthy:

- `hypercode-core`
- PostgreSQL
- Redis
- MinIO
- Chroma
- Memstream
- `hypercode-ollama`
- `healer-agent`
- `safety-shepherd`
- `crew-orchestrator`
- `agent-registry`
- `coder-agent`
- `coder-studio`
- `qa-engineer`
- `skillweaver`
- `fcc-proxy`
- `throttle-agent`
- brain and synchronization services

`throttle-agent` reported a healthy Docker connection, healthy healer connection, a fresh GREEN signal, and low Memstream pressure. FCC returned successful internal model-list responses through its healthcheck.

### Services requiring follow-up

The runtime inventory also showed several services in `Created` state rather than `Running`:

- `celery-worker`
- `hypercode-dashboard`
- `hypercode-mcp-server`

These services should be started explicitly after `hypercode-core` remains healthy. Their `Created` state is not equivalent to a healthy or available service.

The observability services previously recorded exit code 137 or other failures:

- Prometheus
- Prometheus Cloud
- Loki
- Tempo
- Alertmanager
- Promtail
- cAdvisor
- Celery exporter
- Grafana Agent
- Grafana
- node-exporter

The exit code 137 events are consistent with resource pressure or external termination during the earlier monitoring launch. `node-exporter` also has a separate exit code 2 event that requires a clean profile launch and log review.

### Runtime inventory drift

The project has multiple historical Compose configurations and separately launched services. This produced orphan warnings for required services such as `fcc-proxy` and `throttle-agent`, and later warnings for services including `governor`, `prometheus-cloud`, and `grafana-agent`.

Orphan status must not be interpreted as unused status. The correct fix is to make required services part of the canonical Compose graph or explicitly document their separate profile command. The project now includes FCC and throttle in the root include graph, which is the right direction.

---

## 4. Architecture strengths

### Strong service decomposition

The platform separates core API, queue processing, data services, agent coordination, safety, governance, memory, model routing, and observability. This supports independent scaling and fault isolation.

### Strong network intent

The Compose files distinguish backend, data, agent, frontend, and observability networks. The data network is internal, and host bindings generally use loopback addresses rather than exposing administrative services to the LAN.

### Scoped Docker control

The project uses separate Docker socket proxies for read, build, and healer-related actions. This is materially safer than mounting the Docker socket into every agent.

### Resource management is present

The project has CPU and memory limits on many services, a RAM signal pipeline, tiered throttle policy, protected service lists, debounce logic, and an observe-only mode. This is a useful foundation for safe enforcement.

### Health and restart behavior

Many services have healthchecks, start periods, `unless-stopped` restart behavior, and JSON log rotation. The project has already addressed several real startup-order and port-collision issues.

### Migration discipline exists

The backend contains Alembic migrations covering identities, agent keys, governance, missions, payments, pets, focus sessions, and operational features. This provides a foundation for controlled schema evolution.

### Operational tooling is extensive

The scripts directory contains backup, health, validation, cleanup, secret initialization, Docker audit, fleet, deployment, and recovery tooling. The next improvement is consolidating these into a smaller supported operator workflow.

---

## 5. Highest-priority risks

### P0: Credentials have been exposed previously

The runtime dump and project environment history contained credentials for application APIs, GitHub, Anthropic, Stripe, Discord, Grafana, database access, JWT signing, MinIO, and other integrations.

Local application secrets were rotated during this work, but third-party credentials cannot be revoked by Compose. The external providers must be rotated or revoked directly.

Required actions:

1. Revoke exposed GitHub tokens and issue least-privilege replacements.
2. Rotate Anthropic, NVIDIA, OpenRouter, Stripe, Discord, Grafana Cloud, Supabase, Pinata, Vercel, and other provider credentials.
3. Rotate webhook secrets that appeared in the runtime dump.
4. Search Git history and CI logs for leaked values.
5. Enable provider audit logs and alert on unexpected use.
6. Keep `.env` as non-secret configuration only.

### P0: Secret files are not yet the only runtime source

`docker-compose.secrets.yml` defines file secrets, but `docker-compose.core.yml` still includes values such as `API_KEY`, JWT material, memory keys, and payment secrets through environment interpolation and `env_file: .env`.

This means the secret overlay exists but does not fully prevent secrets from entering container environment blocks.

Target state:

- Use file-based secret variables wherever application code supports them.
- Remove `env_file: .env` from services that do not need non-secret configuration.
- Keep only non-sensitive settings in `.env`.
- Add explicit service-level secret declarations for every consumer.
- Add CI checks that fail when known secret key names are assigned through Compose environment interpolation.

### P0: Mutable image references

The project uses multiple `latest` references, including local images and external infrastructure images. Examples include MinIO, Chroma, Grafana Agent, Celery exporter, Docker MCP Gateway, local agent images, SkillWeaver, and some core services.

Mutable tags reduce reproducibility and make rollback difficult.

Target state:

- Pin every external image to a reviewed version.
- Record image digests for production or release builds.
- Use release tags for locally built images rather than `latest`.
- Generate a machine-readable image bill of materials during CI.
- Upgrade dependencies through controlled pull requests rather than implicit rebuilds.

### P1: Canonical Compose contract is still incomplete

The root include graph now includes FCC and throttle, but the runtime still has services launched from older Compose files and temporary Compose paths. The project therefore has more than one operational truth.

Target state:

- Root Compose is the supported default.
- Optional workloads are activated only through documented profiles.
- No required service is started from a temporary file.
- A CI check compares running Compose labels against the supported include graph.
- A clean-machine smoke test starts the supported stack from scratch.

### P1: Created services are not operationally complete

The dashboard, MCP server, and Celery worker were observed in `Created` state during the audit. Core startup ordering and healthcheck timing caused dependency waits in earlier restarts.

Target state:

- Start Core, then run a dependency-aware startup for worker, dashboard, and MCP.
- Add realistic start periods to all database-dependent services.
- Add a smoke test that fails if any required service remains `Created`.
- Add endpoint checks for dashboard, MCP, Celery heartbeat, and Core.

### P1: Observability resource budget is too large for constrained hosts

The observability profile has substantial aggregate memory reservations and several services have historical OOM exits. Prometheus, Tempo, Loki, Grafana, cAdvisor, Promtail, and profiling services should not all be assumed to run continuously on an 8 GB Docker Desktop allocation.

Recommended modes:

- **Lean:** Core health, application metrics, throttle metrics, and external Grafana Cloud.
- **Developer:** Prometheus plus Grafana, short retention, no Loki or Tempo.
- **Full:** Prometheus, Grafana, Loki, Tempo, profiling, and exporters on a larger host.

Do not enable Full mode by default on the current workstation.

### P1: Database and cache persistence need tested recovery

PostgreSQL and Redis have persistent volumes and backup scripts, but the report evidence does not prove a recent restore has been tested. A backup that has never been restored is an assumption, not a recovery plan.

Required actions:

- Perform a PostgreSQL logical backup and restore into a disposable database.
- Restore Redis data into a disposable instance and verify key expectations.
- Back up MinIO and Chroma data according to their durability requirements.
- Record backup age, size, checksum, and restore result.
- Schedule recovery drills.

---

## 6. Security upgrade plan

### Immediate controls

- Revoke all credentials exposed in runtime output or historical files.
- Confirm `.env`, `secrets/`, provider token files, and private key files are ignored by Git.
- Remove credential values from service `environment:` blocks where file-secret support exists.
- Set file permissions on secrets to owner-only where the host filesystem permits it.
- Replace shared application keys with per-service identities.
- Keep `THROTTLE_MODE=observe` until enforcement is tested on disposable services.
- Keep socket proxies restricted to the smallest possible API surface.
- Review `docker-socket-proxy-build` separately because build capability has a larger impact than read-only inspection.

### Container hardening

Apply consistently to services that do not need elevated privileges:

- `no-new-privileges:true`
- `cap_drop: [ALL]`
- non-root user
- read-only root filesystem where compatible
- writable temporary filesystem only where needed
- explicit `tmpfs` for temporary files
- no host network mode
- loopback-only host ports for administrative endpoints
- bounded log rotation
- pinned image digest

Some services, including cAdvisor and Docker control proxies, require special capabilities. Keep those exceptions isolated and documented.

### Supply-chain controls

- Run Docker Scout or Trivy in CI for every release image.
- Fail releases on unresolved critical vulnerabilities unless an approved exception exists.
- Produce SBOM and provenance metadata.
- Sign release images.
- Use a private registry for release artifacts.
- Separate development images from release images.
- Avoid installing dependencies from floating requirements where practical; use lockfiles or hashes.

---

## 7. Reliability and platform upgrade plan

### Compose topology

Keep the current layered structure, but formalize these profiles:

| Profile | Purpose |
|---|---|
| default | Core API, database, Redis, Memstream, Model Runner shim, required agent control plane, FCC, throttle |
| `dashboard` | Dashboard and MCP-facing UI services |
| `workers` | Celery and asynchronous workers |
| `discord` | BROski Bot and Discord integrations |
| `agents` | Optional specialist and utility agents |
| `brain` | Obsidian and brain integrations |
| `observability-lite` | Prometheus, Grafana, throttle metrics |
| `observability-full` | Loki, Tempo, profiling, exporters, cAdvisor |
| `grafana-cloud` | Remote-write and cloud telemetry |

The default profile should contain only services required for the primary product path.

### Startup orchestration

Use a staged startup sequence:

1. Create networks and validate secret files.
2. Start PostgreSQL and Redis.
3. Start Model Runner shim, Memstream, and MinIO/Chroma.
4. Start Core and wait for `/health`.
5. Start Celery, dashboard, MCP, orchestration, healer, safety, FCC, and throttle.
6. Start optional agents and observability profiles.
7. Run smoke tests.

This avoids using one large `up` operation as the only orchestration mechanism.

### Healthcheck improvements

Healthchecks should test useful dependencies without creating cascading startup deadlocks.

Recommended checks:

- Core: database, Redis, and application readiness.
- Celery: heartbeat or worker inspect with a bounded timeout.
- Dashboard: actual application health endpoint.
- MCP: protocol endpoint or health endpoint.
- FCC: authenticated `/v1/models` response.
- Throttle: Docker proxy, healer, and signal status.
- Memstream: authenticated health endpoint.
- MinIO: liveness and a controlled bucket check.

### Resource budget

Create a resource budget file or CI check with maximum aggregate reservations. A practical local budget should define separate limits for:

- Core data plane.
- Agent control plane.
- AI/model plane.
- Optional observability.
- Build-time resource usage.

Throttle-agent should remain the runtime guard, but CI should prevent a Compose change from silently exceeding the host budget.

---

## 8. AI routing and model strategy

### Current model path

The platform supports several model routes:

- Docker Model Runner through the Ollama-compatible shim.
- FCC proxy for free-LLM-compatible workflows.
- NVIDIA NIM through FCC configuration.
- OpenRouter fallback.
- Anthropic provider integrations.
- Agent-specific model settings.

This flexibility is valuable, but the current environment has multiple model variables and provider paths spread across `.env`, Compose files, agent files, and application code.

### Recommended next level

Create a single model gateway contract:

- `MODEL_PROVIDER=local|fcc|nim|openrouter|anthropic`
- `MODEL_ROUTE_DEFAULT`
- `MODEL_ROUTE_FALLBACKS`
- per-task policy for coding, research, chat, and safety
- request timeout and retry policy
- token and cost accounting
- model health and circuit-breaker metrics

FCC should become one implementation behind the model gateway, not a separate configuration universe.

For local models:

- Pin model identifiers.
- Maintain a tested model catalog.
- Record context size and expected memory impact.
- Define automatic fallback behavior.
- Test model availability at startup without blocking Core indefinitely.

---

## 9. Data and persistence plan

### PostgreSQL

- Keep migrations as the only schema-change mechanism.
- Disable automatic schema creation in production after migration confidence is established.
- Add migration checks to CI.
- Add connection-pool saturation metrics.
- Create a read-only reporting role for Grafana.
- Separate application, governance, and analytics access where practical.

### Redis

- Document each logical database and ownership.
- Keep queue and cache policies separate.
- Review `allkeys-lru` against durable queue expectations.
- Monitor evictions, blocked clients, memory fragmentation, and AOF rewrite duration.
- Add queue depth and task age alerts.

### MinIO and Chroma

- Pin images and define explicit storage backup procedures.
- Add bucket initialization checks.
- Record Chroma collection counts and backup expectations.
- Avoid treating local Docker volumes as a complete disaster-recovery strategy.

---

## 10. Observability upgrade plan

### Minimum production signals

Track:

- Core request rate, latency, and error rate.
- PostgreSQL pool usage and migration state.
- Redis memory, evictions, queue depth, and latency.
- Celery task age, failures, retries, and worker heartbeat.
- Agent health and restart counts.
- FCC model availability and provider error rates.
- Throttle signal level and simulated/enforced decisions.
- Healer circuit state and recovery actions.
- Host memory pressure and Docker Desktop memory availability.

### Alert priorities

Create alerts with clear ownership:

- Core unavailable for two consecutive checks.
- PostgreSQL unavailable or migration incomplete.
- Redis evictions or queue age above threshold.
- Celery heartbeat missing.
- FCC provider unavailable or repeated 401/5xx responses.
- Throttle signal RED or stale signal file.
- Healer circuit open for a critical service.
- Container restart loop.
- OOM or exit code 137.
- Backup older than the approved recovery-point objective.

### Keep monitoring lean by default

The existing dashboards are a strength, but the entire telemetry stack should not be required for local product development. Start with Prometheus and Grafana or use Grafana Cloud. Enable Loki, Tempo, profiling, and exporters only when their diagnostic value justifies the memory cost.

---

## 11. CI/CD and release engineering

### Required pipeline stages

1. Compose syntax validation.
2. Secret-name and plaintext-secret scanning.
3. Python lint and type checks.
4. Backend unit and integration tests.
5. Dashboard tests and end-to-end smoke tests.
6. Database migration validation.
7. Docker builds with cache.
8. Image vulnerability scan.
9. SBOM and provenance generation.
10. Clean Compose startup in an isolated runner.
11. Health and endpoint smoke checks.
12. Release image signing and registry push.

### Release artifacts

Publish:

- versioned image tags
- immutable image digests
- merged Compose configuration for the release
- migration version
- SBOM
- healthcheck results
- backup and restore verification result
- rollback command

### Build optimization

The project contains a large number of Dockerfiles and broad build contexts. Improve build time and cache stability by:

- using service-specific contexts
- keeping dependency manifests before source copies
- using BuildKit cache mounts
- avoiding `apt-get upgrade` in every application image unless required by the security policy
- pinning base images
- using multi-stage builds for Python and Node production services
- excluding reports, caches, test databases, local models, and generated artifacts from contexts

The root `.dockerignore` is intentionally broad, but each service should have a tested service-specific ignore file so required source paths are not accidentally excluded.

---

## 12. Recommended implementation roadmap

### Phase 1: Stabilize the default path

- Confirm external credential rotation.
- Start and verify Core, dashboard, MCP, and Celery.
- Add a single supported PowerShell launcher.
- Make FCC and throttle part of every default launch.
- Keep throttle in observe mode.
- Add a smoke test that rejects `Created` services.
- Add a clean restart test that preserves volumes.

### Phase 2: Finish secret migration

- Remove application secrets from `.env`.
- Convert Core, Celery, FCC, throttle, dashboard, HyperHealth, and agent services to file-secret or managed-secret loading.
- Add secret scanning to pre-commit and CI.
- Replace shared keys with service-specific keys.

### Phase 3: Pin and secure the supply chain

- Replace all `latest` image references.
- Pin external images by version and digest.
- Add SBOM, vulnerability scanning, and image signing.
- Standardize Python and Node base images.
- Migrate priority services to hardened base images where compatible.

### Phase 4: Establish resource-aware operations

- Define Lean, Developer, and Full profiles.
- Add aggregate memory-budget validation.
- Tune Prometheus, Loki, Tempo, and profiling retention.
- Start observability-lite first.
- Move throttle from observe to enforce only after simulation evidence and recovery tests.

### Phase 5: Production control plane

- Push release images to a private registry.
- Deploy with immutable versions.
- Separate development, staging, and production Compose environments.
- Add external database and object-storage backup targets.
- Add restore drills and release rollback automation.
- Consider Kubernetes only after the single-host Compose path is deterministic and operationally measured.

---

## 13. Definition of next-level readiness

HyperCode V2.4 is ready for the next stage when all of the following are true:

- A new machine can start the supported stack from documented commands.
- No required service is launched from a temporary Compose file.
- No production service depends on a mutable `latest` image.
- No secret value is passed through the normal `.env` path.
- Core, dashboard, MCP, Celery, FCC, throttle, healer, and safety services pass health checks.
- A clean restart preserves PostgreSQL, Redis, MinIO, Chroma, and agent state.
- A PostgreSQL restore has been completed and verified.
- The default profile stays within the host resource budget.
- Observability-lite runs without OOM events.
- Throttle-agent has documented observe and enforce runbooks.
- CI produces a signed, scanned, reproducible release artifact.
- Rollback has been tested, not merely described.

---

## 14. Final recommendation

Do not expand the service count yet. Consolidate the platform around a supported default launch, complete secret migration, pin the supply chain, finish the dashboard/MCP/Celery startup path, and establish a resource-budgeted observability profile.

The strongest immediate upgrade is an operator-grade release workflow: validate Compose, check secrets, build immutable images, start in dependency order, run endpoint smoke tests, collect health evidence, and retain a tested rollback. This will convert the existing broad capability set into a dependable platform that can safely grow.


---

## 15. Progress update - 2026-10-16 (same day as the assessment)

Verified against the running stack and merged in PR #599.

### Done
| Report item | Result |
|---|---|
| Core healthy, `Created` services started | `hypercode-core` was "degraded" (JWT secret not mounted; MinIO credentials never passed to core). Fixed; core, MCP, Celery and dashboard now start and pass health checks. |
| Smoke test that rejects `Created`/degraded | `scripts/stack-smoke.ps1` (also fails on core `status != ok`, dead endpoints, no Celery heartbeat). |
| Tested PostgreSQL recovery | The old backup script had never worked (wrong role). Rewritten; restore drill passes (35/35 tables, migration `023`). |
| Redis / MinIO / Chroma recovery | Backup + restore drill for all three, each restored into throwaway no-network containers. |
| Scheduled backups with recovery evidence | Three daily Task Scheduler jobs plus checksums, manifests and retention. |
| Off-machine copy | Second-disk mirror plus an AES-256 archive delivered to Google Drive. |
| Alerting | `scripts/backup_watchdog.ps1`: failed/stale backups, disk space, Redis memory/policy -> Discord + toast, de-duplicated. |

### Found while doing it (not in the original report)
- **Chroma lost data on recreate:** it persists to `/data` but the volume was mounted at `/chroma/chroma`. Fixed and proven.
- **Redis `allkeys-lru` could silently evict durable state** (Celery broker, approvals, registry, task state share db0 with TTL'd cache). Changed to `volatile-lru`.
- **Redis lost its restart policy** in an uncommitted edit; restored.
- **`.env` `API_KEY` was blanked by the 15 Oct secret rotation, but the hyperhealth app only reads `API_KEY` from the environment** (no `API_KEY_FILE` support). `main`'s hyperhealth definitions require `API_KEY` in `.env`, so the canonical file set does not validate without it. Fix in progress: teach the app to read the secret file, then change the compose files.

### Still open from this report
P0 credential rotation at the providers; finishing the secret migration (section 6); image pinning (`latest`); formal profiles (section 7); resource-budget CI check; observability-lite; off-site copies of Redis/MinIO/Chroma beyond the daily archive; signed release artifacts.
