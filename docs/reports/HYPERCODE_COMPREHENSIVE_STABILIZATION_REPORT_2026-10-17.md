# HyperCode V2.4 Comprehensive Stabilization Report

**Assessment date:** 17 October 2026  
**Project:** HyperCode V2.4  
**Compose project:** `hypercode-v24`  
**Host:** Windows Docker Desktop with Linux containers and WSL2  
**Report status:** Stabilization changes applied and validated

---

## Executive summary

HyperCode V2.4 is a multi-plane AI-agent platform built around a FastAPI core, PostgreSQL, Redis, Celery, Docker Model Runner routing, Memstream, Chroma, MinIO, a dashboard, MCP services, agent orchestration, safety and healing services, FCC free-LLM routing, a resource throttle, Discord and Obsidian integrations, and optional observability.

The platform is operationally broad and currently functional. The latest runtime snapshot shows the primary services healthy, including Core, PostgreSQL, Redis, Celery, dashboard, MCP server, HyperHealth, BROski Pets, Governor, FCC proxy, throttle-agent, healer-agent, safety-shepherd, agent registry, MinIO, Chroma, Memstream, and the coding/orchestration services.

The main constraint is the 8 GB workstation, not the application feature set. The system has experienced memory pressure, WSL stalls, unhealthy containers during high load, stale RAM-guard signals, and historical OOM exits in the full observability profile. The project should now prioritize operational control, deterministic automation, and resource discipline over adding more agents.

### Current result

- Compose configuration validates.
- Workflow YAML validation passes.
- RAM-guard and JWT rotation focused tests pass.
- 37 focused tests pass.
- Required application services are healthy.
- Governor secret files are now real files rather than Docker-created directories.
- HyperHealth no longer uses the removed hard-coded database URL fallback.
- HyperHealth response modeling now sanitizes credentials embedded in check targets.
- Public API-key fallback values were removed or neutralized in active Compose paths.
- Duplicate workflow triggers and duplicate workflow permissions were repaired.
- One encrypted backup remains queued while Google Drive delivery is unavailable.
- RAM-guard is fresh but currently reports `AMBER` because WSL available memory is below the build floor.

---

## 1. Platform architecture

### Core data plane

- `hypercode-core` is the primary FastAPI application.
- PostgreSQL stores application, governance, agent identity, mission, payment, pet, and operational state.
- Redis provides queue transport, cache behavior, logical database separation, and agent coordination.
- Celery processes asynchronous jobs.
- `hypercode-ollama` provides a stable service name for the Docker Model Runner Ollama-compatible endpoint.
- Memstream provides memory/local-model support.
- Chroma provides persistent vector storage.
- MinIO provides S3-compatible object storage.

### Agent control plane

- `crew-orchestrator` coordinates agents.
- `agent-registry` provides fleet registration and health visibility.
- `healer-agent` handles recovery workflows.
- `safety-shepherd` provides policy and safety decisions.
- `governor` handles governance and capability-related actions.
- `coder-agent`, `coder-studio`, `qa-engineer`, `skillweaver`, and brain services extend the agent platform.

### AI routing plane

- FCC proxy is available on `127.0.0.1:8083`.
- FCC can route requests through local Model Runner, NVIDIA NIM, OpenRouter, and optional providers.
- Agents use the stable `hypercode-ollama` service name rather than direct host coupling.
- The proxy is a required project component because it supplies the free-LLM route.

### Resource-control plane

- `throttle-agent` is available on `127.0.0.1:8014`.
- It monitors Docker/container behavior and consumes the host-side RAM signal.
- It uses the scoped Docker socket proxy rather than a direct Docker socket mount.
- It currently runs in `observe` mode and does not pause containers automatically.
- This is the correct safety posture until the signal writer and recovery paths have been tested under stress.

### Observability plane

The project contains Prometheus, Grafana, Loki, Tempo, Pyroscope, Promtail, cAdvisor, Alertmanager, Celery exporter, Grafana Agent, and Grafana Cloud configuration.

This is a strong diagnostics capability, but it is too large to run by default on an 8 GB development host. Historical exit code 137 events show that full observability can contribute to memory pressure.

---

## 2. Current runtime state

### Healthy primary services

The latest runtime inspection shows these services running and healthy or operational:

- PostgreSQL
- Redis
- MinIO
- Chroma
- Memstream
- `hypercode-ollama`
- `hypercode-core`
- `celery-worker`
- `hypercode-dashboard`
- `hypercode-mcp-server`
- `hyperhealth-api`
- `hyperhealth-worker`
- `broski-pets-bridge`
- `governor`
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
- brain, synchronization, and supporting services

### Intentionally stopped or profile-gated services

The following observability services remain stopped or have historical stopped records:

- Grafana
- Prometheus
- Prometheus Cloud
- Loki
- Tempo
- Pyroscope
- Promtail
- Alertmanager
- cAdvisor
- node-exporter
- Celery exporter
- Grafana Agent

This is appropriate for the constrained host. They should be enabled selectively, not all at once.

### Service operating model

The fleet should be treated as capacity-managed rather than all-on. The field report recorded 17 live agents from a larger 42-agent fleet, with additional agents deliberately down or undeployed because of the 8 GB host limit.

That is not a product failure. It is the correct operating model until the platform moves to a larger host or a distributed deployment.

---

## 3. Resource and memory assessment

### Current RAM-guard state

The scheduled task is installed and running:

- Task: `\HyperCode\HyperCode RAM Guard Signal`
- Run mode: current user, limited privileges
- Signal path: `ram-signal\ram.json`
- Signal freshness: current, under one minute during validation
- Host free memory: approximately 949 MB
- Host compression: approximately 1.4 GB
- WSL available memory: approximately 1.475 GB
- WSL swap used: approximately 1.0 GB
- Overall signal: `AMBER`

The host has recovered from the extreme pressure described in the system test, but WSL remains below the project’s GREEN build floor of 1.5 GB. Do not start builds or full observability while this remains `AMBER`.

### Previous failure pattern

The system test recorded:

- Windows free memory near 95–190 MB.
- WSL load average around 22–24, with a previous spike to 126.
- Multiple unhealthy containers during the stall.
- Memory compression above 3 GB.
- WSL/RAM guard task failure.
- Historical OOM exits from multiple observability services.

### Resource recommendations

1. Keep the default stack limited to core product services.
2. Stop optional services by name rather than using broad Compose teardown.
3. Keep throttle-agent in observe mode until signal resilience is proven.
4. Use a GREEN-only gate for builds, image upgrades, and large restarts.
5. Add an aggregate Compose memory-budget check to CI.
6. Use separate Lean, Product, Research, and Full Observability modes.
7. Move full observability to a larger machine or hosted telemetry when needed.

### Suggested profiles

#### Lean

- Core
- PostgreSQL
- Redis
- Memstream
- Model Runner shim
- Celery
- dashboard
- MCP server
- FCC proxy
- throttle-agent
- healer-agent
- safety-shepherd
- orchestrator

#### Product

Lean plus:

- HyperHealth API and worker
- BROski Pets bridge
- selected coding/QA agents
- agent registry
- brain services required for the daily workflow

#### Research

Product plus selected research agents, only when RAM is GREEN.

#### Observability

Start with Prometheus and Grafana only. Enable Loki, Tempo, profiling, exporters, and cAdvisor only when diagnostic value justifies the memory cost.

---

## 4. Security improvements completed

### Governor secret integrity

The report identified two paths that were directories rather than files:

- `secrets/agent_api_key_governor.txt`
- `secrets/governor_operator_key.txt`

These directories were created by Docker when a bind-mount source was missing. They were replaced with valid files.

The Governor agent key was minted through the existing key-minting tool and registered in the database. The operator key was generated separately and was not reused from the master API key.

### HyperHealth database URL protection

HyperHealth previously had a hard-coded database URL fallback containing database credentials. That fallback was removed from the main API and worker paths.

The API response model now sanitizes credentials embedded in check targets before returning them. A target containing a URL such as `postgresql://user:[REDACTED]@host/db` is returned without the username/password authority portion.

Required follow-up:

- Migrate existing stored check targets to non-secret logical targets.
- Use service configuration or file secrets at execution time.
- Add an API regression test proving passwords never appear in `/checks` responses.

### Public fallback keys

The project previously used values such as `dev-master-key` when secret interpolation failed. These fallbacks are unsafe because the value is public and could silently become active if a secret file is missing.

Active Compose paths were changed to avoid the public default and to use empty inactive-profile values where necessary for Compose validation. Runtime services using required authentication should still fail closed at application startup when their secret file is missing.

The target behavior is:

- No public fallback key.
- Required active services refuse startup if authentication material is missing.
- Inactive profiles may validate without secrets, but must not start authenticated services with an empty key.
- Startup checks must reject directories, empty files, and default values.

### Retired secret backups

The earlier system test found retired JWT, dashboard-token, and inter-agent-key backups on disk. These should be deleted after the new credentials have been verified and any rollback requirement has expired.

The most important cleanup is the retired JWT backup that was previously exposed through a session. Gitignore protection is not sufficient against local disk compromise.

### External credential rotation

Compose changes cannot revoke third-party credentials. The following provider credentials should be rotated directly if they appeared in the earlier runtime dump:

- GitHub
- Anthropic
- NVIDIA NIM
- OpenRouter
- Stripe
- Discord
- Grafana Cloud
- Supabase
- Pinata
- Vercel

Provider audit logs should be checked after rotation.

---

## 5. RAM-guard and throttle-agent status

### Completed

- RAM-guard scheduled task installed.
- Task runs under a limited user context.
- Signal file is updated atomically.
- Throttle-agent reads the signal file.
- Docker control is routed through a scoped proxy.
- Throttle remains in observe mode.
- RAM-guard unit tests pass.

### Remaining risk

The WSL signal is still `AMBER` because available memory is below the build floor. The guard is fresh, but the machine is not yet in a safe state for image builds or full-stack restarts.

### Recommended next-level behavior

- Add timeout and fallback handling for WSL calls.
- Add Windows-native fallback metrics where possible.
- Alert when signal age exceeds two polling intervals.
- Add a scheduled-task restart alert.
- Test stale-signal behavior explicitly.
- Do not change to `THROTTLE_MODE=enforce` until a controlled simulation proves pause/resume and recovery behavior.

---

## 6. Backup and disaster recovery

### Working controls

- PostgreSQL backups are being generated.
- Redis, MinIO, and Chroma store backups are being generated.
- Checksums are written and verified.
- Encrypted 7z archives are generated.
- Restore drills previously passed.
- Second-disk copies are verified.

### Current issue

The latest off-site run created and verified the encrypted archive but could not deliver it because Google Drive for Desktop was not mounted or signed in.

Current state:

- Local second-disk copy: verified.
- Encrypted archive: verified.
- Off-site destination: unavailable.
- Queued encrypted archive: one.
- Scheduled task result: `0x2`, meaning waiting for Drive.

### Manual action

Start or sign in to Google Drive for Desktop, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\backup-offsite-task.ps1 -Action start
```

Verify:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\backup-offsite-task.ps1 -Action status
```

The report should show an encrypted archive in `G:\My Drive\HyperCode-Backups` and zero queued archives.

### Further backup recommendations

- Add a second independent off-site destination.
- Keep the encryption passphrase in a password manager.
- Test recovery from the off-site archive quarterly.
- Alert if off-site delivery has not succeeded within one backup cycle.
- Keep local backup retention separate from cloud retention.
- Protect the backup directory against accidental deletion by cleanup scripts.

---

## 7. CI/CD repair

### Problems found

The system test found 22 workflow files with duplicate top-level `on:` keys. Several workflows also contained duplicate `permissions` mappings. GitHub rejects these files before jobs execute.

`ci-cd.yml` also referenced a nonexistent `test` job while the actual job was named `lint-and-test`. Its Python setup step had been populated with Trivy options rather than a Python version.

### Fixes applied

- Removed duplicate `on:` trigger entries.
- Removed duplicate `permissions` mappings.
- Added `scripts/validate_workflow_yaml.py` with duplicate-key rejection.
- Added the validator to the Docker workflow.
- Changed the `ci-cd.yml` build dependency to `lint-and-test`.
- Repaired the Python setup block to install development dependencies and run focused tests.

### Validation

The workflow validator now passes across the workflow directory.

### CI next steps

1. Open a focused CI repair pull request.
2. Run workflow syntax checks first.
3. Observe the first real workflow failures separately.
4. Repair genuine test/environment failures after syntax is clean.
5. Do not merge all Dependabot major upgrades together.
6. Process patch/minor upgrades first.
7. Handle Tailwind, MCP, mypy, and Pylint major upgrades individually.
8. Add a required workflow that rejects duplicate YAML keys.

### CI resource policy

The 8 GB workstation should not be used as the only place for full Docker build and integration validation. Heavy builds belong in GitHub Actions or a remote builder. Local builds should require a GREEN RAM-guard result.

---

## 8. Test and validation results

The following checks passed during the stabilization work:

- Workflow YAML validation.
- Compose configuration validation.
- Python syntax compilation for changed Python files.
- RAM-guard tests: 24 passed.
- JWT rotation tests: 13 passed.
- Combined focused tests: 37 passed.
- Current application service health snapshot.
- Governor secret file type checks.
- RAM signal freshness check.
- Encrypted backup verification.
- Second-disk backup checksum verification.

The full dashboard suite, full throttle suite, and full observability launch were not rerun during the final stabilization pass because the host remained `AMBER` and the project intentionally avoids adding heavy load under memory pressure.

---

## 9. Current risks still open

### High priority

- Google Drive delivery is waiting for manual sign-in.
- WSL memory remains below the GREEN build floor.
- External provider credential rotation must be completed outside Docker.
- Retired secret backups should be deleted after rollback confidence is confirmed.
- HyperHealth existing stored check targets should be sanitized or migrated.

### Medium priority

- The full observability profile has historical OOM exits.
- Some services still use mutable `latest` image references.
- Local development and release Compose configurations are not fully separated.
- Full fleet capacity exceeds the practical 8 GB workstation budget.
- Watchdog alerts need deliberate-test markers to reduce false positives.
- Some agents do not emit heartbeats consistently.

### Low priority

- Intentional stopped observability containers create historical noise in `docker ps -a`.
- Docker Desktop extension ports should be reviewed for non-loopback exposure.
- Grafana checks should distinguish intentionally disabled services from failures.
- The economy consumer’s historical timeout lines should remain monitored, though reconciliation passed.

---

## 10. Recommended operating procedures

### Before a build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\ram-guard-task.ps1 -Action status
```

Proceed only when the signal is GREEN.

### Before a restart

```powershell
docker compose ps -a
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\ram-guard-task.ps1 -Action status
```

Do not run broad teardown commands that remove required FCC or throttle services.

### After a restart

```powershell
docker compose ps -a
docker compose config --quiet
```

Then confirm:

- Core healthy.
- PostgreSQL healthy.
- Redis healthy.
- Celery worker healthy.
- Dashboard healthy.
- MCP server healthy.
- FCC proxy healthy.
- throttle-agent healthy.
- RAM signal fresh.

### Before enabling observability

- Confirm RAM-guard is GREEN.
- Start Prometheus and Grafana first.
- Wait for healthchecks.
- Add Loki and Tempo only if memory remains stable.
- Avoid starting every exporter simultaneously.

---

## 11. Recommended roadmap

### Phase 1: finish stabilization

- Sign in to Google Drive and deliver the queued archive.
- Confirm one successful off-site run with status `0x0`.
- Keep the RAM guard active.
- Remain in throttle observe mode.
- Delete retired secret backups after rollback confirmation.
- Add HyperHealth response regression tests.

### Phase 2: finish CI recovery

- Commit workflow repairs in a focused pull request.
- Observe all revived workflows.
- Fix real failures by category.
- Add duplicate-key validation as a required gate.
- Add a GREEN-resource guard to local Docker build scripts.

### Phase 3: security hardening

- Complete external provider credential rotation.
- Remove secrets from `.env` wherever file-secret support exists.
- Pin all external images.
- Remove `latest` from release paths.
- Add image scanning, SBOM generation, and provenance.
- Add startup refusal for missing, empty, directory, or public-default secret files.

### Phase 4: capacity management

- Formalize Lean, Product, Research, and Full Observability profiles.
- Add aggregate memory budget validation.
- Move heavy builds to CI or remote BuildKit.
- Reduce default agent count on the workstation.
- Test throttle enforcement with disposable services.

### Phase 5: production readiness

- Publish immutable release images.
- Separate development, staging, and production configuration.
- Test rollback from a prior image set.
- Test restore from off-site backups.
- Add external monitoring for backup freshness and service health.
- Consider multi-node orchestration only after the single-host Compose path is deterministic.

---

## 12. Definition of done

HyperCode V2.4 should be considered stabilized when:

- Google Drive off-site delivery succeeds.
- RAM-guard remains fresh across a full day and survives WSL interruption tests.
- Core, dashboard, MCP, Celery, FCC, throttle, Governor, HyperHealth, and safety services pass health checks after a clean restart.
- No active service can fall back to a public key.
- HyperHealth never returns database credentials.
- Workflow YAML validation passes in CI.
- All required workflows execute at least once successfully.
- The default Compose profile stays within the workstation memory budget.
- Observability-lite runs without OOM exits.
- A PostgreSQL and stores restore drill passes from an off-site archive.
- Release images are pinned and reproducible.
- Rollback is tested rather than only documented.

---

## Final assessment

HyperCode V2.4 is a capable and increasingly mature AI-agent platform. Its strongest foundations are the service decomposition, persistent data plane, health and recovery tooling, safety layer, scoped Docker control, FCC routing, throttle-agent, dashboard, and migration history.

The project’s next level is operational discipline. The most valuable work is now:

1. Complete off-site backup delivery.
2. Keep the RAM guard active and respect its AMBER/GREEN gates.
3. Finish CI recovery.
4. Complete secret migration and cleanup.
5. Keep the default fleet within the 8 GB host budget.
6. Enable full observability only on a larger host or through hosted telemetry.
7. Adopt immutable, scanned, reproducible release images.

The platform does not need more features before these controls are complete. It needs dependable recovery, predictable resource use, and trustworthy automation around the features already built.
