# HyperHealth FastAPI / Starlette Upgrade Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Remove every known vulnerability from the `agents/hyperhealth` image (15 app-level advisories: starlette 7, cryptography 6, pyOpenSSL 2) by moving FastAPI/Starlette forward and deleting two unused dependencies, with no change to the service's behaviour.

**Architecture:** This is a dependency change, not a code change. `agents/hyperhealth/requirements.txt` is edited; a permanent HTTP smoke test and a small CI job are added so the next upgrade is checked automatically; then the image is rebuilt and the two running services (`hyperhealth-api`, `hyperhealth-worker`) are recreated one at a time with a rollback tag.

**Tech Stack:** Python 3.11 (image `python:3.11-slim`), FastAPI, Starlette, uvicorn, SQLAlchemy asyncio, pytest + pytest-asyncio, GitHub Actions, Docker Compose (`hyperlaunch.ps1`).

**Spec:** none; the evidence below plays that role.

## Evidence (gathered 2026-10-19, read-only)

- Current pins: `fastapi==0.115.2` (pulls `starlette 0.40.0`), `pyOpenSSL==24.2.1` (pulls `cryptography 43.0.3`), `slowapi==0.1.9`.
- **`pyOpenSSL` is unused**: nothing imports `OpenSSL` or `cryptography`; `worker.py`'s `import ssl` is the standard library. It was added in the original "Clean start" commit with no stated reason. Removing it also removes `cryptography` and `cffi`.
- **`slowapi` is unused**: it is in `requirements.txt` only; no file imports it or uses a limiter.
- FastAPI use is light: `FastAPI`, `Depends`, `HTTPException`, `Header`, `Query`, `PlainTextResponse`, a lifespan, 11 routes with `response_model`. No middleware, no WebSockets, no StaticFiles.
- FastAPI 0.149.0 requires only `starlette>=0.46.0` (no upper bound) and `pydantic>=2.9.0`, so Starlette 1.x is allowed. Starlette 1.3.1 is the version that clears the last advisory; pip resolved 1.9.0.
- **Experiment**: two scratch venvs on Python 3.11, (A) current pins, (B) candidate = current minus `pyOpenSSL` and `slowapi`, `fastapi==0.149.0`, `starlette>=1.3.1`.
  - Existing tests: **20 passed on both**.
  - A throwaway HTTP smoke test (18 requests: health, metrics, auth missing/bad/ok, validation 422s, 404s, openapi, docs) gave **identical status codes on A and B**.
  - `pip-audit` on the installed environments: A = 25 advisories, B = 10, and those 10 are the venv's own `pip`/`setuptools` (not in the image). App-level: 15 → 0.
- The hyperhealth tests are **not run by any CI workflow today**, so this upgrade has no automatic safety net until Task 2.
- Starlette 1.x prints a deprecation warning when its `TestClient` is used with `httpx` ("install `httpx2` instead"). Tests only; not a runtime issue.

## Global Constraints

- No application code changes in `agents/hyperhealth/*.py` (behaviour must stay identical); only `requirements.txt` and new test/CI files.
- Every pin in `requirements.txt` stays an exact `==` pin (the file's existing style); add `starlette` as an explicit exact pin so a future resolve cannot drift back to a vulnerable range.
- Python stays 3.11.
- Never print or log secret values (`API_KEY` / `secrets/*`).
- Deploy one container at a time, health-gated, with a rollback image tag (`rollback/hyperhealth:20261019`) taken before the recreate. Use `.\hyperlaunch.ps1 --profile health ...` (4-file compose set), never plain `docker compose`. Host RAM is tight (about 0.7 GB free): do not start other heavy work during the build/recreate.
- Do not touch other agents' requirements in this change (they have their own FastAPI/Starlette pins; see "Next").

## Review Focus

- Auth: a missing `X-API-Key` still returns 422 and a wrong key 401 on every protected route (Header dependency behaviour is the most Starlette-sensitive part).
- `response_model` and `Query` validation (`limit` max 500, bad UUID in the path) return the same status codes as before.
- The lifespan still starts (it needs the real database; verified in Task 4, not by the smoke test).
- `/metrics` output is still valid Prometheus text.
- Nothing else in the image breaks when `cryptography`/`cffi` disappear (asyncpg, httpx, redis must not need them).

---

### Task 1: Change the requirements

**Files:**
- Modify: `agents/hyperhealth/requirements.txt`

**Interfaces:** Produces the pin set Task 2 tests and Task 4 builds.

- [ ] **Step 1: Edit** `requirements.txt`: delete the `pyOpenSSL==24.2.1` and `slowapi==0.1.9` lines; change `fastapi==0.115.2` to `fastapi==0.149.0`; add `starlette==1.9.0`.
- [ ] **Step 2: Verify resolution** on Python 3.11: `py -3.11 -m pip install --dry-run --ignore-installed --prefer-binary -r agents/hyperhealth/requirements.txt` exits 0. Expected: no conflict; no `cryptography`, `cffi`, `pyopenssl`, `slowapi` or `limits` in the install list; `opentelemetry-api`, `typing-inspection`, `annotated-doc` are new transitive installs.
- [ ] **Step 3: Commit** (`fix(hyperhealth): FastAPI 0.149 / Starlette 1.9, drop unused pyOpenSSL and slowapi`).

### Task 2: Permanent HTTP smoke test and CI

**Files:**
- Create: `agents/hyperhealth/tests/test_api_smoke.py`
- Create: `.github/workflows/hyperhealth-tests.yml`

**Interfaces:** Consumes the pins from Task 1.

- [ ] **Step 1: Write** `test_api_smoke.py` from the throwaway script: set the same env vars as `test_main.py` before import, override `main.get_db` with a fake async session (`execute` returns an object with `scalars().all() == []`, `scalar_one_or_none() is None`, `scalar() == 0`; `get` returns `None`), use `TestClient(main.app)` **without** entering the context manager (the lifespan needs a real DB). One test per case with its expected status: `GET /health` 200; `GET /metrics` 200; `GET /checks` no key 422, bad key 401, good key 200; `GET /checks?enabled_only=maybe` 422; `GET /checks/not-a-uuid` 422; `GET /checks/{uuid}` 404; `GET /checks/{uuid}/results?limit=501` 422 and `limit=10` 200; `POST /checks` `{}` 422; `DELETE` and `PATCH /checks/{uuid}` 404; `GET /health/report` 200; `POST /selfheal/trigger` without `service` 422; `GET /openapi.json` 200 and 7 paths. Leave out the `POST /checks` invalid-URL case (it hits the fake DB's `refresh`, not validation).
- [ ] **Step 2: Run on the OLD pins first** (`git stash` the requirements change or use a venv with the old file): expected **PASS**, which proves the test describes today's behaviour and is not tailored to the new stack.
- [ ] **Step 3: Run on the NEW pins**: `cd <repo root> && PYTHONPATH=. pytest agents/hyperhealth/tests -q`. Expected: 20 existing + the new smoke tests all pass.
- [ ] **Step 4: CI**: create `hyperhealth-tests.yml`, path-filtered to `agents/hyperhealth/**` and the workflow file, on `pull_request` and `push` to `main`; steps: checkout, setup-python 3.11 with pip cache, `pip install -r agents/hyperhealth/requirements.txt pytest pytest-asyncio`, `PYTHONPATH=. pytest agents/hyperhealth/tests -q` from the repo root (the tests patch `agents.hyperhealth.worker`, so the working directory matters). Expected: green on the PR.
- [ ] **Step 5: Commit** (`test(hyperhealth): HTTP smoke test and a CI job so dependency bumps are checked`). Open one PR with Tasks 1 and 2; wait for all checks; merge. No running container changes yet.

### Task 3: Prove the image builds and is clean

**Files:** none (verification).

- [ ] **Step 1: Build** from `main` after the merge: `docker build -f agents/hyperhealth/Dockerfile -t hyperhealth:candidate agents/hyperhealth`. Do this when nothing else heavy is running. Expected: success; image size within a few percent of the current one.
- [ ] **Step 2: Audit the image**: `docker run --rm hyperhealth:candidate pip list` contains `starlette 1.9.0`, `fastapi 0.149.0` and none of `cryptography`, `cffi`, `pyOpenSSL`, `slowapi`; run `pip-audit` against the image's site-packages (or Trivy, as CI does). Expected: no advisories for the app's packages.

### Task 4: Deploy (api first, then worker), with rollback

**Files:** none (operations; needs Lyndz's go-ahead for the recreate).

- [ ] **Step 1: Rollback tag**: `docker tag <current hyperhealth image> rollback/hyperhealth:20261019` for the images used by `hyperhealth-api` and `hyperhealth-worker`.
- [ ] **Step 2: Recreate `hyperhealth-api`** with `.\hyperlaunch.ps1 --profile health up -d --no-deps --force-recreate hyperhealth-api`; wait for `healthy`. Verify with the real key read from the secret file (never printed): `GET /health` 200, an authenticated `GET /checks` 200 and an unauthenticated one 422, `GET /metrics` 200. Check the logs for errors from the lifespan and the database connection.
- [ ] **Step 3: Recreate `hyperhealth-worker`** the same way; wait for `healthy`; confirm in its log that a check cycle ran and wrote results (the worker is what produces the data the API serves).
- [ ] **Step 4: Watch** for 10 minutes: no unhealthy containers, no 401/5xx from hyperhealth in the dashboard or logs.
- [ ] **Step 5: Rollback if anything fails** (any step above): put the previous image back with the `rollback/hyperhealth:20261019` tag (retag it as the compose image name), recreate the same service, and re-verify; then report what failed.

### Task 5: Close out

- [ ] **Step 1:** Update `docs/` / memory notes (what changed, new CI job, rollback tag kept for a few days) and delete the rollback tag after a few quiet days.
- [ ] **Step 2:** Re-run the repo-wide pin audit to record the new baseline (hyperhealth removed from the list).

## Risks and how they are covered

| Risk | Cover |
|---|---|
| Starlette 1.x changes request/response edge cases | 18-request smoke comparison on old vs new (identical); permanent smoke test; real-key checks in Task 4 |
| Lifespan or DB startup breaks (not testable without Postgres) | Task 4 verifies on the real stack and has a rollback |
| `cryptography` removal breaks a transitive user | Resolution dry run (no conflict) and 20 + smoke tests pass; image `pip list` and the real start in Task 4 |
| New transitive packages (`opentelemetry-api` etc.) | Small, pure-Python; pinned by the resolver at build time; reviewed in Task 1 step 2 |
| RAM pressure during build/recreate (0.7 GB free) | Do it in a quiet window, one container at a time, health-gated |

## Next (not in this plan)

- Other FastAPI services still pin old Starlette ranges (for example `agents/mission-executor` fastapi 0.109.1, which keeps `starlette<0.36`); each needs the same treatment with its own tests.
- `uvicorn 0.31.1`, `httpx 0.27.2` and `pydantic-settings 2.5.2` are old but not flagged; bump with the next pass.
- Starlette's `TestClient` wants `httpx2`; switch the test dependency when convenient.
