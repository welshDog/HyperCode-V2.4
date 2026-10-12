# HyperCode Upgrade Report

## 1. Scope

This report covers the project improvements completed during the upgrade session:

- Backend Docker build optimization.
- CI workflow correction and reliability improvements.
- Rate-limit initialization hardening on Windows and local development environments.
- Docker image build and runtime verification.
- Compose, lint, workflow, import, and targeted test validation.
- Security scan execution and its documented limitation.

The repository is a large HyperCode platform containing a FastAPI backend, agent services, dashboards, infrastructure configuration, observability components, and multiple Docker Compose layers.

## 2. Changes Completed

### 2.1 Backend Dockerfile

Updated `backend/Dockerfile` with the following changes:

- Added the Dockerfile frontend syntax directive:

  ```dockerfile
  # syntax=docker/dockerfile:1.7
  ```

- Added a BuildKit pip cache mount to the builder dependency installation step:

  ```dockerfile
  RUN --mount=type=cache,target=/root/.cache/pip \\
      pip install -r requirements.txt && \\
      if [ "$INSTALL_AI_DEPS" = "true" ]; then pip install -r requirements-ai.txt; fi
  ```

- Preserved dependency installation before application source copying, maintaining effective layer reuse.
- Removed duplicate pip, setuptools, wheel, and jaraco installation from the runtime stage.
- Continued copying installed packages from the builder into the runtime image.
- Kept compiler packages out of the runtime stage.
- Preserved the non-root `appuser` runtime configuration.
- Preserved the existing HTTP healthcheck against `/health`.
- Preserved optional AI dependencies behind `INSTALL_AI_DEPS`.

### 2.2 GitHub Actions Python Workflow

Updated `.github/workflows/ci-python.yml`:

- Corrected dependency path filters from root-level requirement patterns to:

  ```yaml
  backend/requirements*.txt
  ```

- Aligned CI with the backend declaration by changing the runner Python version from 3.11 to 3.12.
- Added backend bytecode compilation:

  ```yaml
  python -m compileall -q backend/app
  ```

- Added an application import smoke check:

  ```yaml
  from app.main import app
  ```

- Kept the full backend test suite after the smoke checks.
- Preserved workflow concurrency cancellation and read-only repository permissions.

The smoke checks run in the existing test job, avoiding a second dependency installation and unnecessary CI cost.

### 2.3 Docker Build Workflow

Updated `.github/workflows/docker-build.yml`:

- Removed the invalid standalone `read` entry under the workflow trigger declaration.
- Restored valid GitHub Actions YAML structure with push and pull-request triggers.

### 2.4 Rate-Limit Middleware

Updated `backend/app/middleware/rate_limiting.py`:

- Reorganized imports to satisfy Ruff import ordering.
- Removed whitespace-only lint violations.
- Prevented slowapi from automatically reading the repository `.env` file.
- Configured slowapi with the platform null device for its optional configuration filename.
- Suppressed only the expected missing-config warning during limiter construction.
- Set `PYTHONUTF8=1` by default to make Windows environment-file handling safer.
- Preserved the existing rate-limit storage selection logic:
  - Test environments use in-memory storage.
  - Explicit rate-limit storage settings remain supported.
  - Redis remains supported when explicitly configured.
  - Internal Compose-only Redis addresses do not force failures outside Compose.
- Preserved endpoint limits and asynchronous Redis limiter behavior.

### 2.5 Generated Artifact Cleanup

Removed accidental Dockerfile backup artifacts created during the earlier editing process:

- `memstream/Dockerfile.bak-2026-10-10`
- `services/hypercode-mcp-server/Dockerfile.bak-2026-10-10`
- `services/skillweaver/Dockerfile.bak-2026-10-10`

Existing changes in `memstream/Dockerfile`, `services/hypercode-mcp-server/Dockerfile`, and `services/skillweaver/Dockerfile` remain in the working tree and were not included in the backend verification scope.

## 3. Docker Image Results

### Image

Built image:

```text
hypercode-core:upgrade-check
```

Build command:

```powershell
docker build --progress=plain -f backend/Dockerfile -t hypercode-core:upgrade-check ./backend
```

Build result:

- Build completed successfully.
- BuildKit cache mounts were accepted and used.
- Dependencies were installed in the builder stage.
- Runtime layers were exported successfully.
- Docker image size: approximately 2.49 GB.
- Runtime user: `appuser`.
- Healthcheck: configured against `/health`.

The large image size is caused primarily by the broad backend dependency set, including scientific, data, agent, observability, and development-oriented packages.

### Runtime Smoke Test

The image was launched with a temporary container and exposed on host port `18000`.

The first request occurred while the application was still completing startup and timed out. Container logs showed that Uvicorn continued startup successfully. A later request returned:

```text
HTTP 200
{"status":"ok","service":"hypercode-core","version":"2.4.2","environment":"test"}
```

The temporary container was removed after verification.

The startup logs also confirmed that unavailable database and Redis services are handled as non-fatal in this isolated smoke configuration. Production deployments should still provide the configured database, Redis, and required secrets.

## 4. Validation Results

### Passed

- Docker Desktop server availability check.
- Backend Docker image build.
- Runtime `/health` HTTP check.
- Non-root image user inspection.
- Docker healthcheck metadata inspection.
- Compose configuration validation:

  ```powershell
  docker compose config --quiet
  ```

- CI workflow YAML parsing.
- Ruff validation for the modified rate-limit module.
- Git whitespace validation:

  ```powershell
  git diff --check
  ```

- Rate-limit test module:

  ```text
  10 passed
  ```

- Backend application import smoke test.
- `/health` route discovery during application import.
- Backend module compilation command added to CI.

### Warnings Remaining

The targeted test run still reports a third-party Starlette pending deprecation warning related to multipart parsing. This warning originates from an installed dependency and does not fail the tests.

Ruff also reports that the project’s top-level configuration keys are deprecated in favor of the newer `lint` configuration section. The modified module itself passes Ruff.

## 5. Security Scan Result

Trivy was run against the built image with high and critical severity filtering and unfixed findings excluded.

The scan successfully:

- Pulled the Trivy scanner image.
- Downloaded the vulnerability database.
- Began scanning the built image.

The scan did not finish within the configured timeout while analyzing large scientific Python binaries, including SciPy native extensions. It ended with a semaphore acquisition timeout during analysis.

This is an incomplete scan, not a clean security result. No claim of zero vulnerabilities should be made until the scan completes.

Recommended follow-up scan command:

```powershell
docker run --rm `
  -v /var/run/docker.sock:/var/run/docker.sock `
  aquasec/trivy:latest image `
  --timeout 30m `
  --scanners vuln `
  --severity HIGH,CRITICAL `
  --ignore-unfixed `
  hypercode-core:upgrade-check
```

## 6. Current Risk Assessment

### Dependency footprint

The backend production requirements contain a very broad set of packages. Several heavy libraries are present even though only selected backend modules import them. This creates:

- A large image.
- Longer dependency resolution time.
- Longer image export time.
- Slower vulnerability scanning.
- A larger potential attack surface.
- More opportunities for dependency resolver conflicts.

### Dependency consistency

The repository contains multiple dependency sources, including:

- `backend/requirements.txt`
- `backend/requirements-UPGRADED.txt`
- `backend/requirements-ai.txt`
- `backend/requirements-dev.txt`
- `backend/pyproject.toml`

These files do not fully describe the same dependency graph. A future controlled consolidation should be performed only after import mapping and test coverage review.

### Runtime startup

The application currently performs multiple startup tasks, including database-related recovery and observability initialization. The service eventually became available during the smoke test, but a readiness probe should allow for this startup period rather than probing immediately after container creation.

### Existing working-tree changes

The working tree contains changes in several Dockerfiles beyond the backend files reviewed in this report. Those files should be reviewed separately before committing the complete working tree.

## 7. Recommended Next Phase

> **Status update (2026-10-11):** Priorities 1–4 were carried out in the follow-up
> session and Priority 3 (Trivy) completed. Priority 5 is still open. Details,
> numbers and open items are in sections 9–12 below.

### Priority 1: Create a slim production dependency set

Use import analysis and service ownership to separate:

- Core API runtime dependencies.
- Agent orchestration dependencies.
- Scientific and vector-search dependencies.
- AI and model dependencies.
- Development and security tooling.

Keep `requirements-ai.txt` optional and prevent model-serving packages from entering the standard API image unless explicitly requested.

### Priority 2: Add a dedicated slim image target

Add a production target using only the core runtime dependency set. Keep the current broad image available for compatibility until the slim image passes integration tests.

Suggested tags:

```text
hypercode-core:slim-check
hypercode-core:production
hypercode-core:ai
```

### Priority 3: Complete the Trivy scan

Run Trivy with a longer timeout after the slim image exists. Compare vulnerability counts and image sizes between the current and slim images.

### Priority 4: Improve readiness verification

Use a readiness endpoint or startup-aware retry loop for container smoke tests. The test should:

1. Start the container.
2. Retry `/health` for a bounded period.
3. Fail with `docker logs` output if readiness is not reached.
4. Remove the temporary container in all cases.

### Priority 5: Consolidate dependency ownership

Choose one authoritative dependency model, then generate or validate the other files from it. Avoid manually maintaining divergent versions across requirements files and `pyproject.toml`.

## 8. Final Status

The completed upgrade is operationally verified at the Docker image and backend smoke-test level.

Confirmed:

- The backend image builds.
- The runtime image uses a non-root user.
- The application starts.
- The `/health` endpoint returns HTTP 200.
- Compose configuration validates.
- CI YAML validates.
- Targeted rate-limit tests pass.
- Modified rate-limit code passes Ruff.
- Git diff validation passes.

Not yet confirmed:

- Completion of the full backend test suite in this final image-build pass.
- A completed Trivy vulnerability scan.
- Production database and Redis integration using real service dependencies.
- A fully slimmed dependency graph.

> Sections 1–8 describe the first upgrade pass and are kept as written. The
> "Not yet confirmed" list above is partly superseded: see section 12 for the
> current status.

---

## 9. Slim Image Phase (follow-up session, 2026-10-11)

### 9.1 Analysis

- Python **3.12** is authoritative: `pyproject.toml` has `requires-python >=3.12`,
  and the Dockerfile base is `python:3.12-slim`. The comment in
  `backend/requirements.txt` that says "we use 3.11" is stale (not yet fixed).
- A static import scan of `backend/app` (137 files) plus `backend/alembic` found
  that the app imports almost none of the heavy libraries pinned in
  `requirements.txt` (308 pins). Zero files import `numpy`, `pandas`, `scipy`,
  `matplotlib`, `scikit-learn`, `qiskit`, `pygame`, `langgraph`, `openai`, or
  `requests`. Dev and security tooling (`black`, `ruff`, `mypy`, `pylint`,
  `bandit`, `coverage`, `factory_boy`, `Faker`, `detect-secrets`, and others) was
  also in the production file.
- Two things the scan alone got wrong, caught by reading the code:
  - `psycopg2-binary` looked tests-only but is a **runtime** dependency. The sync
    engine (`app/db/session.py`) and Alembic use `postgresql://`, and the
    container CMD runs `alembic upgrade head` first.
  - `chromadb` cannot be dropped. `app/api/v1/endpoints/memory.py` imports
    `app/core/rag.py` at startup, and its `DefaultEmbeddingFunction()` fallback
    runs a local ONNX model (needs `onnxruntime` and `numpy`). It stays in the
    core set for now and is the largest remaining weight.
- `passlib` and `requests` are not used by `app/` or `alembic/` (`requests` appears
  only in the root script `backend/hypercode.py`), so both were left out of core.

### 9.2 New files (backend/)

| File | Purpose |
|---|---|
| `requirements.core.in` | About 40 **direct** dependencies for the core API runtime, each with a reason. Source of truth. |
| `requirements.core.txt` | Compiled lockfile for Python 3.12 on Linux: **154 pins** (down from 308). Generated, do not hand-edit. |

Regenerate with (versions are held to the known-good pins in `requirements.txt`):

```bash
uv pip compile requirements.core.in -c requirements.txt \
  --python-version 3.12 --python-platform linux -o requirements.core.txt
```

### 9.3 Dockerfile: opt-in slim build path

`backend/Dockerfile` gained a `DEPS_VARIANT` build arg. The default is `full`, so
the default image is built the same way as before.

- `build-base`: shared OS and pip hardening, used by both variants.
- `builder` / `deps-full`: installs `requirements.txt` (and `requirements-ai.txt`
  when `INSTALL_AI_DEPS=true`), as before.
- `deps-core`: installs `requirements.core.txt` only. `INSTALL_AI_DEPS` is
  intentionally ignored on this path.
- `deps`: `FROM deps-${DEPS_VARIANT}`, the selected set. The runtime stage copies
  site-packages from `deps`, so the user, healthcheck, and `alembic upgrade head`
  CMD are written once and shared by both images.

```bash
# slim build
docker build -f backend/Dockerfile --build-arg DEPS_VARIANT=core \
  -t hypercode-core:slim-check ./backend
```

`docker build --check` reports no warnings for the default, `full` and `core`
runs. The runtime stage is still last, so it remains the default target.

### 9.4 Build and runtime results

| | `upgrade-check` (full) | `slim-check2` (slim, current pins) |
|---|---|---|
| Image size | 2.49 GB | **1.18 GB** (about 53% smaller) |
| Runtime user | `appuser` | `appuser` |
| `/health` | HTTP 200 | HTTP 200, `{"status":"ok","service":"hypercode-core","version":"2.4.2","environment":"test"}` |
| Time to ready | n/a | 80 s to 233 s depending on the run (see 10.4) |
| Idle memory | n/a | about 183 MiB |

- First slim build: 8m29s. Docker Desktop's image store reports a partial size
  until unpacking finishes, so wait for the build log's `unpacking ... done`
  before reading the size.
- Inside the slim image `scipy`, `pandas`, `matplotlib`, `sklearn`, `qiskit`,
  `pygame`, `torch`, `langgraph`, `openai`, `black` and `pytest` are absent;
  `alembic`, `psycopg2`, `asyncpg` and `chromadb` import fine.
- Readiness probes should allow 5 minutes or more on first start (see 10.4).
- A pre-existing pip warning appears in both images: the Dockerfile's hardening
  step installs `jaraco.text>=4.0.0`, which pulls in `typer-slim` (needs
  `typer>=0.24`), and the pinned `typer==0.16.0` is then installed over it. It
  only affects `jaraco.text`'s own CLI. Not changed.

---

## 10. Security Scan Results (Priority 3, completed)

Trivy was run with `--timeout 30m --scanners vuln --severity HIGH,CRITICAL
--ignore-unfixed`. Each scan finished in about 2 minutes; the SciPy binaries that
stalled the earlier scan are gone from the slim image. The Debian base layers have
**0** fixable HIGH/CRITICAL findings in every image; all findings are pinned
Python packages.

| Image | Fixable HIGH + CRITICAL |
|---|---|
| `upgrade-check` (original, full set) | 57 (3 critical) |
| `slim-check` (slim, old pins) | 19 (2 critical) |
| `slim-check2` (slim, bumped pins) | **7 (0 critical)** |

### 10.1 Pin bumps applied

To clear the slim image's CRITICAL and most HIGH findings, six pins were raised.
They live in `backend/requirements.txt`, which is the constraint source for the
core lockfile, so they apply to the full image as well:

| Package | From | To |
|---|---|---|
| `anyio` | 4.9.0 | 4.14.2 (was the remaining CRITICAL) |
| `PyJWT` | 2.12.0 | 2.14.0 |
| `pyasn1` | 0.6.3 | 0.6.4 |
| `urllib3` | 2.7.0 | 2.8.0 |
| `python-multipart` | 0.0.27 | 0.0.30 |
| `fsspec` | 2026.3.0 | 2026.6.0 |

`backend/pyproject.toml` was kept in step for the two packages it pins: `PyJWT`
2.14.0 and `python-multipart` 0.0.30 (it previously said 0.0.26).

### 10.2 Remaining 7 HIGH findings (all need larger moves)

| Package | Installed | Fixed in | Note |
|---|---|---|---|
| `starlette` | 0.49.1 | 1.1.0 / 1.3.1 (2 findings) | Major-version jump; FastAPI must support it. |
| `cryptography` | 46.0.7 | 48.0.1 / 49.0.0 / 50.0.0 (3 findings) | Two or more major versions. |
| `httpcore2` | 2.3.0 | 2.10.0 | Unfamiliar package name; find what pulls it in first. |
| `httpx2` | 2.3.0 | 2.12.0 | As above. |

These carry real break risk (FastAPI, `python-jose`, `slowapi`) and should be
changed in a separate pass with the full test suite, not bundled with the safe
bumps above.

### 10.3 Follow-up: `cryptography` and `starlette` upgrades (applied, tested, not yet rescanned)

| Package | From | To | Note |
|---|---|---|---|
| `cryptography` | 46.0.7 | 50.0.2 | At or above the fix version for all 3 findings (not yet rescanned). Resolved cleanly alongside `python-jose`, `PyJWT`, `rsa`, `ecdsa`. |
| `starlette` | 0.49.1 | 1.7.0 | At or above the fix version for both findings (1.3.1 or newer; not yet rescanned). |
| `prometheus-fastapi-instrumentator` | 7.1.0 | 8.1.0 | Required: 7.1.0 declares `starlette<1.0.0`. Also bumped in `pyproject.toml`. |

- `fastapi` stays at 0.135.3. It already allows `starlette` 1.x, so no change was
  needed. `fastapi` 0.143.0 was **avoided** on purpose: it requires
  `opentelemetry-api>=1.44.0`, which would have forced the whole OpenTelemetry
  family up.
- `slowapi` stays at 0.1.9; `sse-starlette` 1.6.1 and `mcp` (full set) accepted
  the new `starlette` in the resolver.
- Both `requirements.txt` and the compiled `requirements.core.txt` resolve. The
  core lockfile diff is exactly these three lines.
- `pyproject.toml` still pins `FastAPI==0.141.0` against `requirements.txt`'s
  0.135.3. That drift predates this work and was not changed.

### 10.4 Last two findings, and the rescan result

The final 2 HIGH findings after the upgrades above were `httpx2` 2.3.0
(CVE-2026-84382) and `httpcore2` 2.3.0 (CVE-2026-84381). Neither is pinned in any of
your files and the app does not import them: they arrive via
`langchain-text-splitters` -> `langchain-core` -> `langsmith` -> `httpx2` ->
`httpcore2`. Fix:

- `requirements.core.in` gained floors `httpx2>=2.12.0` and `httpcore2>=2.10.0`
  (with a comment explaining why).
- `httpx2` 2.12.0 or newer needs `idna>=3.18`, which conflicted with the
  `idna==3.10` pin in `requirements.txt`; `idna` was bumped to **3.20**.
- The core lockfile diff is exactly three lines: `httpx2` 2.13.1, `httpcore2`
  2.13.1, `idna` 3.20. The full `requirements.txt` set also resolves.

**Rescan of `hypercode-core:slim-check4` (slim image, final pins): 0 fixable
HIGH/CRITICAL findings** (Debian 0, Python 0), using the same Trivy settings as
before. Installed versions in the image were confirmed directly: `starlette`
1.7.0, `cryptography` 50.0.2, `idna` 3.20, `httpx2` 2.13.1, `httpcore2` 2.13.1,
`anyio` 4.14.2, `PyJWT` 2.14.0. `app.main`, `alembic`, `psycopg2`, `asyncpg`,
`chromadb` and `langchain_text_splitters` all import.

| Image | Fixable HIGH + CRITICAL |
|---|---|
| `upgrade-check` (original, full set) | 57 (3 critical) |
| `slim-check` (slim, old pins) | 19 (2 critical) |
| `slim-check2` (slim, safe bumps) | 7 (0 critical) |
| `slim-check3` (slim, + cryptography / starlette) | 2 |
| **`slim-check4` (slim, final pins)** | **0** |

Scope of that "0": HIGH and CRITICAL only, vulnerabilities only, and
`--ignore-unfixed` (findings with no upstream fix are excluded by design). It is
not a claim that the image has no vulnerabilities, and it covers only the slim
image; see section 12 for the full image.

**Startup time is slow and highly variable.** On the same code, `/health` took from
about 80 s up to 233 s to answer in the test environment (one run passed only after
102 s, another had not answered at 270 s, while the previous image took 233 s on
the same harness). The log goes quiet after `DBPoolCollector registered`. This
looks like startup work waiting on unreachable Postgres/Redis hosts in the
isolated smoke setup (consistent with section 6, "Runtime startup"), but the exact
wait was not diagnosed. Readiness probes and smoke tests should allow 5 minutes or
more, not 90 s.

---

## 11. Test Suite on the Bumped Pins

- A throwaway Python 3.12 venv was built from the core set (Windows-platform
  compile of `requirements.core.in` under the same `-c requirements.txt`
  constraints) plus test tooling. Confirmed installed: `anyio` 4.14.2, `PyJWT`
  2.14.0, `pyasn1` 0.6.4, `urllib3` 2.8.0, `python-multipart` 0.0.30, `fsspec`
  2026.6.0, `starlette` 0.49.1, `fastapi` 0.135.3.
- Test-only extras the core set does not include: `pytest`, `pytest-asyncio`,
  `pytest-xdist`, `minio`, `fakeredis`, `faker`, `factory-boy`, `respx`,
  `aiosqlite`, and `structlog` (needed by `tests/unit/test_goal_keeper_framework.py`,
  which imports `agents/goal_keeper/main.py`).
- **1,113 tests collect with no import errors.**
- Run: serial, `ENVIRONMENT=test`, `-m "not e2e"` (the `e2e` tests need live
  services; the `e2e` mark is also unregistered and produces
  `PytestUnknownMarkWarning`).
- Result: **1,060 passed, 44 failed, 6 skipped** (3 deselected as `e2e`), 18m54s.
  **None of the 44 failures is caused by the pin bumps.** Triage:

| Failures | Cause | Pin-related? |
|---|---|---|
| 40 in `tests/test_operator_mcp_tools.py` | `ModuleNotFoundError: No module named 'mcp.server'`. These tests load `services/hypercode-mcp-server/server.py`, a separate service that owns `mcp`; `mcp==1.26.0` is in the full `requirements.txt` but deliberately not in the backend core set. Nothing in `backend/app` or `backend/alembic` imports `mcp`. Test-environment gap, not a slim-image gap. | No |
| 3 in `tests/unit/test_agent_pulse.py` | `module 'app.agents.pulse' has no attribute 'requests'`. `pulse.py` was moved from `requests` to `httpx` on 2026-07-09 (commit `f635dbc1`); the tests still patch `pulse_mod.requests`. Stale tests. | No |
| 1 in `tests/test_crew_pause.py::test_a_step_in_flight_finishes_then_the_run_holds` | `assert [] == ['a']` at line 74: after a fixed 0.1 s sleep, step `a` has not started. Fails identically with the **old** pins (`anyio` 4.9.0, `PyJWT` 2.12.0, `pyasn1` 0.6.3, `urllib3` 2.7.0, `python-multipart` 0.0.27, `fsspec` 2026.3.0) and with the new ones, and reproduces when run alone. A fixed-delay timing assumption; root cause not diagnosed (possibly slow startup on this Windows host). | No (identical on old pins) |

  The other 1,060 tests, including everything under the app, auth, middleware and
  rate-limit areas, pass on the bumped pins. This does not cover the 40 `mcp`
  tests (they need `mcp` installed) or the `e2e` tests (they need live services).

**Second run, with the `cryptography` / `starlette` / instrumentator upgrades
(section 10.3):** a fresh venv on the full new stack (`starlette` 1.7.0,
`cryptography` 50.0.2, `prometheus-fastapi-instrumentator` 8.1.0) gave
**44 failed, 1,060 passed, 6 skipped** in 20m05s, and the set of failing test IDs is
**identical** to the first run (compared by sorted test ID). `from app.main import
app` also imports cleanly with 137 routes. So the upgrades introduced no
regressions the suite can see, and no test that passed before fails now.

---

## 12. Current Status and Open Items

### Confirmed

- Slim image builds and starts; `/health` returns HTTP 200; runs as `appuser`.
- Image size 2.49 GB to 1.18 GB; fixable HIGH/CRITICAL findings 57 to 7, with no
  CRITICAL remaining.
- Trivy completes on both images.
- The six pin bumps resolve cleanly for both the full and the core sets.
- The slim image runs against a real Postgres and Redis: migrations to head `022`,
  seeding, a full auth flow and a wallet write all work (section 14.1).
- All work is merged to `main` (PRs #552, #553, #557, #556, #558; section 14.3) and
  the four agent images, `build-backend` and `test-compose` pass in CI on `main`.

### Not yet confirmed

- The rate limiter was not triggered in any test, and nothing exercised Stripe, MinIO
  or other external services. RAG against a real Chroma server is now covered (see
  section 16), including the full login-to-RAG chain.
- The slim image was rebuilt and rescanned on the final pins (0 fixable
  HIGH/CRITICAL, section 10.4). The **full image was rebuilt on the same pins**
  (`hypercode-core:full-check`, 2.5 GB; it builds and exports, but no container
  smoke test was run on it). Its Trivy rescan was **started but not completed**: the
  scan was stopped by Claude Code because the machine ran critically low on memory
  (the orphaned scanner container was then stopped by hand). There is therefore no
  post-bump vulnerability number for the full image; the last measured figure is the
  pre-bump 57 (section 10). Rerun it only when the RAM guard is GREEN, on its own.
- The 7 HIGH findings listed in section 10.2 were resolved by the section 10.3 /
  10.4 upgrades; the slim image rescans at 0. They are not re-measured on the full
  image (see the item above).
- The **running stack** has not been rebuilt: the live `hypercode-core` predates the
  `langchain-text-splitters` pin and the writable-`HOME` fix, so RAG there is very
  likely still affected until it is rebuilt from `main` (section 14.2).
- The pre-existing, uncommitted Dockerfile changes in `memstream`,
  `services/hypercode-mcp-server` and `services/skillweaver` noted in section 6 are
  still unreviewed and were deliberately not part of any of these PRs.

### CI findings on the first PR run

CI built the backend image from this Dockerfile (`build-backend`) and passed
`security-scan`, `Trivy`, `lint`, `CodeQL` and `GitGuardian`. `Python Tests` ran 625
tests (621 passed, 4 failed). In CI the 40 `mcp` tests and the `crew_pause` timing
test pass, so the local failure counts earlier in section 11 reflect that local
test environment (no `mcp` installed; slow host), not the code.

- **`test_core_rag.py::test_rag_ingest_document_chunks_and_adds` (real bug, fixed
  here):** `app/core/rag.py` falls back to `RecursiveCharacterTextSplitter = None`
  when `langchain_text_splitters` is missing, and it was listed only in
  `requirements-ai.txt`. The default `requirements.txt`, and therefore CI and the
  default image (`INSTALL_AI_DEPS=false`), had no splitter, so RAG ingest chunking
  was broken there. `requirements.txt` now pins it with its closure
  (`langchain-text-splitters`, `langchain-core`, `langchain-protocol`, `langsmith`,
  `truststore`, plus the `httpx2` / `httpcore2` CVE floors). The slim image already
  had it. The core lockfile pins did not change.
- **3 `test_agent_pulse.py` tests (fixed here):** stale since `pulse.py` moved to
  `httpx` (commit `f635dbc1`); they patched `pulse_mod.requests.get` with a sync
  fake. They now patch the shared `pulse_mod._http.get` with an async fake
  (`async def fake_get(url, params)`). Assertions are unchanged. These 3 plus the 4
  `test_core_rag.py` tests pass locally (7 passed).
- **`build-agents` (4 jobs) and `test-compose`:** pre-existing workflow defects,
  fixed afterwards in #553 (section 14.3). The workflow used `./agents/<name>`
  paths but the folders are `agents/01-frontend-specialist` and so on; `coder` needs
  a locally built `agent-base` image; `test-compose` needed a `.env`, two required
  variables, `agents.yml` validated together with core, and Compose v5.5.1 (the
  runner's v2.38.2 rejects the repo's `include:` of several files that each declare
  `agents-net`).

### Operational lesson

During the smoke test the smoke container, a Trivy scan and a debug container were
started together and exhausted host RAM (17 MB free, Memory Compression at 4.8 GB),
which made Docker unresponsive and made the app look "not ready". It was not an
app fault: the same image answered `/health` once it ran alone on a GREEN
`python scripts/ram_guard.py --for build`. Run build, smoke test and Trivy **one at
a time** and gate each on the guard.

### Suggested next steps

1. Rebuild the running `hypercode-core` from `main` (with the RAM guard GREEN and
   the stack owner's go-ahead) to pick up the splitter pin and the `HOME` fix.
2. Rerun the full image's Trivy scan on its own when the machine has headroom;
   there is still no post-bump number for it.
3. Decide whether normal (non-superuser) users should be able to retrieve memory at
   all (section 16.3). The embedding model is now baked into the image (section 17).
4. Consider `chromadb-client` or server-side embeddings to remove most of the
   `numpy` / `onnxruntime` weight, and lazy-load `chromadb` (about 11 s of import).
5. Fix the stale "3.11" comment in `requirements.txt`, and Priority 5
   (consolidate dependency ownership).
6. Several other workflows (`trivy-weekly`, `hyper-agents-gate2-e2e`,
   `promote-dashboards`, ...) fail instantly with "workflow file issue" (invalid
   YAML). Not touched here.

---

## 13. Startup Time: Cause and Bytecode Precompile (slim image)

### Cause

The 80 s to 230 s (and sometimes longer) the slim image took to answer `/health`
was **Python import time, not database or Redis waits**. `python -X importtime -c
"import app.main"` took about 88 s of cumulative import time (111 s with container
start) on the test host. No single import dominates (`chromadb` ~11 s; `fastapi`,
`sqlalchemy`, `redis.asyncio` 6-8 s each). The code that runs after import is
bounded: the Redis ping is capped at 2 s and HyperFlow recovery at 15 s (its
database work runs in threads, so the cap holds).

The Dockerfile sets `PYTHONDONTWRITEBYTECODE=1` and never precompiled anything, so
every cold start recompiled all of `site-packages` from source.

### Change

The `core` variant now precompiles bytecode: `site-packages` in the `deps-core`
stage (`--invalidation-mode unchecked-hash`, safe because the image is immutable)
and the app's own `app/` and `alembic/` in the runtime stage (default timestamp
mode, so a bind-mounted newer source is still picked up). The `full` variant is
unchanged.

### Measured results

| Measurement | Without `.pyc` | With `.pyc` |
|---|---|---|
| `import app.main` (same container, compiled in place) | 109 s cold / 101 s warm | 63 s / 55 s |
| `import app.main` (baked into the image) | n/a | 46 s / 55 s |
| Container start to `/health` HTTP 200 | 102 s to >233 s across runs | 84 s |

Roughly a 2x import speed-up. Timings on this host move a lot with machine load
(one run during heavy Docker load took 287 s for a single import, which is why that
run was discarded), so treat the exact seconds as indicative, not guaranteed.

Cost: 10,155 `.pyc` files, **148 MB** in `site-packages` (exact bytes), and about
+80 s of build time. The listed image size of `pyc-check` (1.06 GB) is lower than
`slim-check4` (1.18 GB) only because the earlier build also copied untracked local
artifacts (`htmlcov`, `coverage.xml`, ...) from the working directory; the new build
came from a clean checkout. A like-for-like size comparison against a clean
no-bytecode build was not made.

### Still open

- Even with bytecode the import takes ~50 s on this host; the import graph is heavy.
  Lazy-loading `chromadb` in `app/core/rag.py` would save about 11 s more, but the
  tests patch it at module level, so it needs a matching test change.
- Readiness probes and smoke tests should still allow several minutes on slow hosts.
- The `full` image was not changed.


---

## 14. Integration Test, RAG Fix and Merge Outcome

### 14.1 Slim image against a real Postgres and Redis

Method: throwaway `postgres:16-alpine` (data on tmpfs) and `redis:8-alpine`
containers on a private network, no volumes, nothing touching the live stack. The
slim image ran its **real default command** (`alembic upgrade head`, then uvicorn)
with `ENVIRONMENT=development` and throwaway credentials. All test containers, the
network and the credentials were removed afterwards.

| Check | Result |
|---|---|
| Migrations from an empty database | Applied cleanly to head `022`; 28 tables |
| `/health` | HTTP 200 after 85 s |
| Redis | Metrics client and cache connected; metrics, heartbeat and log keys present |
| Startup seeding | 5 achievements seeded by the app |
| HyperFlow recovery | Ran against the database (`resume/complete/fail/skip` all 0 on an empty DB) |
| Create user | Row stored with a hashed (not plaintext) password |
| Login, `/users/me` with token | 200 |
| Wrong password / no token / duplicate email | 400 / 401 / 400 |
| Daily login | Created 1 wallet and 1 transaction |
| Errors in the core log | 0 tracebacks, 0 ERROR lines |

This ran on `starlette` 1.7.0, `cryptography` 50.0.2 and `PyJWT` 2.14.0. A first
user-creation attempt returned 422 because the test used a reserved `.invalid`
address; `email-validator` rejected it correctly, and a normal address then worked.

Not exercised: the rate limiter (nothing tripped it), a Chroma server, and anything
needing Stripe, MinIO or other services.

### 14.2 RAG embedding crash and fix (PR #557)

`app/core/rag.py` tries `SentenceTransformerEmbeddingFunction` and falls back to
chromadb's `DefaultEmbeddingFunction()` (a local ONNX model), which caches under
`$HOME/.cache/chroma`. `appuser` is created with `adduser --system`, so
`HOME=/nonexistent`, and the first embedding call raised
`PermissionError: [Errno 13] ... '/nonexistent'`. `sentence-transformers` is only
installed with `INSTALL_AI_DEPS=true`, so in the default image this fallback is the
only embedding path.

Fix: `ENV HOME=/app/cache` just before `USER appuser` (that directory is already
created and owned by `appuser`). Verified on a freshly built image with no override:
`appuser`, `HOME=/app/cache` writable, and 2 x 384-dimension embeddings returned.
The first call downloads the 79 MB model (167 MB cached), so it needs outbound
internet.

The live `hypercode-core` container and the default full image were checked read-only
and have the same conditions (`HOME=/nonexistent`, no `sentence_transformers`). RAG
there very likely fails until rebuilt from `main`, but no data was written to the
live stack, so the end-to-end failure there is inferred, not proven.

### 14.3 What was merged, and CI on `main`

| PR | Change | Merge commit on `main` |
|---|---|---|
| #552 | Slim core image, pin bumps, earlier CI/rate-limit fixes, this report | `e2dfe4ef` |
| #553 | `docker-build.yml`: agent paths, `agent-base` for `coder`, compose validation | `85fc7680` |
| #557 | Writable `HOME` for RAG embeddings | `c1b59d01` |
| #556 | Bytecode precompile for the slim image | `7baa4fd2` |
| #558 | Trivy SARIF upload: `upload-sarif@v3` and `security-events: write` | `6ecd4801` |

On the first run of `Docker Build & Test` on `main` (`7baa4fd2`), the four agent
builds, `build-backend`, `build-spawner`, `lint` and `test-compose` all passed;
`security-scan` failed in its upload step only (deprecated `upload-sarif@v2` and no
`security-events` permission), which #558 fixed.

After #558 (`6ecd4801`), `Docker Build & Test` on `main` passes in full: all four
`build-agents`, `build-backend`, `build-spawner`, `lint`, `security-scan` and
`test-compose` succeed, and `CI — Python`, `Security — CodeQL` and the health check
pass too.

Other workflows (for example `tests.yml`, `health.yml`, `swarm-pipeline.yml`,
`no-legacy-paths.yml`, `sse-tests.yml`) still show an instant `failure` on `main`.
GitHub lists a workflow by its file path instead of its name when it cannot parse
the file; for `no-legacy-paths.yml` the run page confirms "This run likely failed
because of a workflow file issue". Those were not touched by this work.


---

## 15. Full Pin Set: Remaining Vulnerable Packages Bumped

The slim image scans at 0, but the default (full) image installs the whole
`backend/requirements.txt`, which still carried vulnerable pins. The full image was
**not rebuilt** for this (it needs a cold 2.5 GB build, which previously pushed the
VM to its memory stop line); instead Trivy scanned the fully pinned file directly
(`trivy fs`, `--severity HIGH,CRITICAL --ignore-unfixed`). All earlier findings were
pinned Python packages (the Debian base had none), so this covers the layer that
matters, but not OS packages.

**Method check:** on the pre-bump pins the file scan found **55** fixable
findings, against **57** from the real image scan earlier. The packages match; the
2-finding gap is packages the Dockerfile installs outside `requirements.txt`.

| Pins | Fixable HIGH + CRITICAL |
|---|---|
| Before the bumps (crew tip `93b6dd15`) | 55 (3 critical) |
| `main` after #552-#559 | 38 (1 critical), in 11 packages |
| This change | **0** |

Bumped to the newest fix version Trivy reported, in three commits:

| Package | From | To | Findings |
|---|---|---|---|
| `GitPython` | 3.1.50 | 3.1.60 | 20 (incl. the only CRITICAL) |
| `tornado` | 6.5.5 | 6.5.9 | 5 |
| `mcp` | 1.26.0 | 1.28.1 | 3 |
| `python-engineio` | 4.12.2 | 4.13.2 | 2 |
| `soupsieve` | 2.7 | 2.8.4 | 2 |
| `aiohttp` | 3.13.4 | 3.14.3 | 1 |
| `msgpack` | 1.1.2 | 1.2.1 | 1 |
| `pyarrow` | 21.0.0 | 23.0.1 | 1 |
| `python-socketio` | 5.14.0 | 5.16.2 | 1 |
| `langgraph-sdk` | 0.3.13 | 0.4.4 | 1 |
| `strawberry-graphql` | 0.312.3 | 0.326.1 | 1 |

Two of those needed a small, measured cascade (found by resolving the whole pinned
set): `langgraph-sdk` 0.4.4 requires `langgraph` 1.2.13, `langgraph-checkpoint`
4.2.0 and `langgraph-prebuilt` 1.1.0 (`langgraph` 1.1.0 capped the SDK below 0.4);
`strawberry-graphql` 0.326.1 requires `cross-web` 0.7.0.

Verified: the full pinned set resolves (315 pins, none resolved to a different
version), none of the bumps introduces a new unpinned package (the 12 existing
unpinned extras are identical to `main`'s), and `pyproject.toml` was updated where it
pinned the same packages. None of these 11 packages is imported by `backend/app` or
is in the slim core set, so the live core image is unaffected.

Not done: the test suite was not run locally against the full set (installing 315
packages on the Windows host is heavy and not representative); the PR's CI installs
the real `requirements.txt` on Linux and builds the default image, which is the
check that matters. The OS layer of the full image was not re-scanned.


---

## 16. RAG End-to-End Tests (2026-10-12)

Both tests ran against a **throwaway Chroma server** (never the live one, so no test
data or `reset` could touch real memories), using the live slim core image
(`hypercode-core:latest`, running as `appuser` with `HOME=/app/cache`). The Chroma
container used the same image as the live stack (`chromadb/chroma:latest`, server
`chromadb` 1.4.4) and its configuration (`ALLOW_RESET=FALSE`, `IS_PERSISTENT=TRUE`,
a tmpfs instead of a volume). Every container, network and credential was removed
afterwards.

### 16.1 The RAG module against a real Chroma server: 19 of 19 checks

The real `app.core.rag.RAGService` was driven directly. Because `query()` swallows
every exception and returns `[]`, results were cross-checked with an independent raw
`chromadb` client.

| Area | Result |
|---|---|
| Client/server versions | Core's client is `chromadb` **1.0.15**; the server is **1.4.4**. They work together for every operation below |
| Connect, create the collection | Works; the collection is visible to an independent client |
| Embeddings | 384-dimensional vectors as non-root with a writable `HOME` |
| Ingest and chunking | 3 short documents (1 chunk each); a 4,400-character document became 6 chunks; chunk metadata (`source`, `chunk_index`, `total_chunks`, custom keys) correct |
| Server-side truth | The server holds exactly the 9 chunks ingested |
| Semantic search | Three differently-themed questions each returned the right document first |
| `n_results` and metadata filters | Respected; a filter with no match returns nothing |
| Persistence | A second, fresh client sees the same data |
| `reset()` | Raises `ChromaError: Reset is disabled by config`; the data stays intact |

### 16.2 The full chain over HTTP: 24 of 24 checks

A throwaway Postgres 16, Redis 8 and Chroma plus the live slim core image, driven
over real HTTP. Two users were created through the API; one was promoted to
superuser directly in the throwaway database (the code says a superuser needs a
manual update). Two checks first looked like failures: a non-superuser calling
ingest or reset gets HTTP **400** ("The user doesn't have enough privileges") from
`get_current_active_superuser`, not the 403 the test assumed. The access control
works, so with the expectation corrected all 24 checks pass.

| Area | Result |
|---|---|
| Login | Both users log in and get JWTs; `/users/me` accepts them |
| Without a token | Ingest and query return 401 |
| Normal user | Ingest and reset are refused (400) |
| Input validation | Empty content, a query over 500 characters and `limit=0` return 422 |
| Superuser ingest | Works; a long document is chunked; the first call took 41 s (model download) |
| Superuser query | Correct document first for both questions; `limit` respected |
| Server-side truth | 7 chunks stored, all stamped `visibility=private` with the admin's user id |
| Reset | 503 `Memory service unavailable`; data survived; the core logged the real reason |
| Core log | The only error was that refused reset |

On a calm host the core was ready in 29 s (precompiled bytecode, section 13). Free
VM memory dipped to 1,190 MB at its lowest, about 10 MB under the 1,200 MB stop line;
the test's abort threshold (1,150 MB) never fired.

### 16.3 Findings

1. **Normal users cannot retrieve any memory.** `POST /memory/query` scopes a
   non-superuser to documents whose `user_id` equals their own, but `POST
   /memory/ingest` is superuser-only and always stamps the *ingesting superuser's*
   id (it overwrites any `user_id` in the request metadata). A normal user's query
   returned 0 results. Nothing leaks, but nothing is retrievable either. If normal
   users are meant to read shared memory, this needs a design change; this report
   records the behaviour, not the intent.
2. **`POST /memory/reset` can never succeed on the live stack.** The live Chroma runs
   with `ALLOW_RESET=FALSE`, so `client.reset()` always raises, and the endpoint
   reports a generic 503 "Memory service unavailable" that does not say reset is
   disabled. It may be deliberate protection.
3. **`query()` hides failures.** Any exception becomes an empty result list, so a
   broken Chroma connection looks like "no results". Check the server directly
   (`chromadb.HttpClient(...).get_collection("hypercode_memory").count()`) when
   diagnosing.
4. **The embedding model downloaded at runtime** (79 MB) and was cached only inside
   the container, so every core recreate downloaded it again and needed outbound
   internet. Fixed by baking it into the image; see section 17.
5. **Minor:** every new `RAGService` logs a harmless "sentence_transformers not
   installed, falling back" warning, and a non-superuser gets 400 rather than the
   conventional 403.

### 16.4 Not covered

The rate limiter (nothing tripped it), concurrent access, documents near the
20,000-character ingest limit, more than one superuser, Stripe, MinIO and other
external services, and the live stack's own Chroma contents (deliberately never
touched; the live core was healthy throughout).


---

## 17. Embedding Model Baked Into the Image

### Problem

`app/core/rag.py` falls back to chromadb's `DefaultEmbeddingFunction`
(`all-MiniLM-L6-v2`, ONNX) unless `sentence-transformers` is installed (only with
`INSTALL_AI_DEPS=true`). That fallback downloaded its model (79 MB) from Chroma's S3
bucket on the first RAG call after every container recreate. It needed outbound
internet, depended on that bucket being up, and made the first call slow.

### Change (`backend/Dockerfile`)

- New stage `model` (`FROM deps`, so both the `full` and `core` variants get it) runs
  the real embedding function once with `HOME=/app/cache`, asserts it returns a
  384-dimension vector, deletes the redundant `onnx.tar.gz` archive, and checks that
  `model.onnx` exists. `HOME` must be set before Python starts because chromadb reads
  `Path.home()` at import time. **The build fails** if the model cannot be fetched or
  loaded, instead of silently shipping an image that still downloads at runtime.
  chromadb verifies the archive's SHA-256 when it downloads it.
- The runtime stage copies the result with
  `COPY --chown=appuser:appuser --from=model /app/cache/.cache /app/cache/.cache`.
  chromadb treats the model as present when its six extracted files exist, so the
  archive is not needed at runtime.
- The existing final `chown -R appuser:appuser /app` now skips `/app/cache`
  (`find /app -path /app/cache -prune -o -exec chown appuser:appuser {} +`). That
  directory is already owned by `appuser`, and a recursive chown would have stored the
  ~90 MB model a second time in its own layer.

### Measured

A first draft with a recursive `chown -R` added **two** 91.4 MB layers (the copy and
the chown). With `--chown` on the copy and the pruned `find`, the model adds one
91.4 MB layer and the ownership step adds 4 kB. Docker's top-line image "Size" figure
for this image store counts extra bookkeeping and over-states the cost, so the
per-layer sizes are the number to trust.

Verified on a test image layered on the live core image with the same steps, running
with **no network at all** (`--network none`), as `appuser`:

| Check | Result |
|---|---|
| Embeddings with the network disabled | Works: 2 vectors x 384 dimensions |
| Archive still present / re-downloaded | No / no |
| `model.onnx` owner and readability | `appuser` (uid 100), readable |
| Cost of the first embedding call, offline | 13 s to load the model; 1.5 s for later calls; plus about 11 s to import `chromadb` |

An earlier single-call timing of 121 s was the host under heavy load (load average
about 14), not the model.

### What this does and does not buy

The first RAG call no longer needs internet, no longer depends on the S3 bucket, and
no longer downloads 79 MB after each recreate. Loading the model still takes about
13 s on this host, and importing `chromadb` still takes about 11 s. The size cost is
about 91 MB per image.

### Not verified

The real Dockerfile was checked for structure (`docker buildx build --print` parses
both variants) but a full cold build of the `core` variant was not run locally (the
build cache had been cleared and a cold build is heavy on this VM). CI's `build-backend`
builds the default `full` variant, which runs the `model` stage for real. The test
above used the same commands layered on the live image.
