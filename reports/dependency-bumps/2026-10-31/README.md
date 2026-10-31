# Backend dependency bumps: evidence (2026-10-31)

Why: the `Security — Comprehensive Scan` job (pip-audit) reported **35 unaccepted vulnerabilities in 13 packages** in the
runtime pins of `backend/requirements.txt` (run `41210492082`). Every one has a fixed version.

The fix is split into two **draft pull requests**, opened so CI could verify them. Neither is merged, and the running containers
still hold the old versions (shipping needs an image rebuild and recreate).

| PR | Branch | What |
|---|---|---|
| **#704** | `deps/bump-runtime-vulns-a` | 12 clean bumps (candidate A): Authlib, GitPython, pyasn1, tornado, Brotli, certifi, filelock, graphql-core, dnspython, langgraph-sdk, msgpack, setuptools |
| **#705** | `deps/bump-opentelemetry-family` | The OpenTelemetry family moved together (18 pins + 2 new) and a real tracing regression test |

They touch different lines, so they merge in either order. Together they take the runtime audit to **0**.

## CI results (what is proven)

| | #704 (A) | #705 (OpenTelemetry) |
|---|---|---|
| Security scan (manual dispatch on the branch) | 35 → **1** (`opentelemetry-api` only) | 35 → **34**; OpenTelemetry cleared, **no new package flagged** |
| Backend suite (`CI — Python`) | ✅ 1,107 passed, 6 skipped (same as main) | ✅ 1,109 passed (the 2 new tests) |
| Docker Build & Test, Trivy, CodeQL, Health Check | ✅ | ✅ |
| `CI/CD` Lint + Test | ✅ | ❌ first run (see "Flaky test"), ✅ on re-run (1,215 passed) |
| Quality Gate | ❌ `npm audit` (same as main) | ❌ same |

Branch pushes alone run **no CI** here: the workflows run on `main` or on pull requests into `main`, and the security scan only on
`main`, a schedule or manual dispatch (`gh workflow run security-comprehensive.yml --ref <branch>`).

## Why OpenTelemetry is separate

`opentelemetry-sdk 1.40.0` requires `opentelemetry-api==1.40.0` exactly, and ~12 instrumentation and exporter packages are tied to
the same release, so a lone bump of `opentelemetry-api` cannot resolve (`dryrun-docker-candidate.log`). Its one finding needs the
whole family: `1.40.0` → `1.45.1` and `0.61b0` → `0.66b1`, plus two packages that were not in the freeze before and are now
pinned (`opentelemetry-exporter-http-transport`, `opentelemetry-exporter-otlp-common`, both `0.66b1`). `protobuf` 6.33.5 and
`grpcio` 1.74.0 are unchanged and install alongside the new proto package.

`tests/conftest.py` sets `OTEL_SDK_DISABLED=true` for the whole suite, so nothing exercised `app.core.telemetry` and an upgrade could
break tracing with every test green. #705 adds `backend/tests/test_telemetry_instrumentation.py`, which runs the real
`setup_telemetry` in a fresh interpreter (tracing sets a process-wide provider) and checks a real request. In `python:3.12-slim` it
passes on the old pins (control) and the new pins, and a negative control (route excluded from tracing) fails the three expected
checks: `smoke-run.log`.

## Local dry-run notes (and why CI was the verifier)

- The current file resolves cleanly with pip in `python:3.12-slim` (`dryrun-docker-baseline.log`, exit 0, ~12 min).
- Local full-file resolver runs for the candidates were cut short by a memory guard (WSL free memory sits on 1,050–1,300 MB; the
  resolver itself uses only ~250–300 MiB) and are slow because `typing`, `PyPika` and `sgmllib3k` ship only as source. CI on a
  full-size runner was the better verifier and is what the table above reports.
- A host-side dry-run on Python 3.13 gave false failures (`audioop-lts; python_version >= "3.13"`): pip evaluates markers against the
  host interpreter. Resolver checks belong inside the image's own Python.
- `pip-audit --no-deps --disable-pip` audits only exact `==` pins; 5 range lines (`pydantic`, `pydantic-settings`, `stripe`) are
  invisible to it, which is why local counts (33) differ from CI (35).

## Flaky test (not caused by these bumps)

The first `CI/CD` run on #705 stopped on `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached` at the
**teardown of `test_a_capped_run_stays_unpaid_when_replayed_tomorrow`** (`backend/tests/test_crew_quests.py`). The new telemetry
tests sort after it and had not run; the re-run passed. Two Dependabot branches failed the same job, so this looks like an
intermittent database-connection leak in that test. It deserves its own fix.

## Not verified / watch after a rebuild

- The running containers and a rebuilt image. Dockerfile strips vendored `setuptools` after install (see the comment near line 148
  of `backend/Dockerfile`), so the image build matters for #704 (`setuptools` 83 → 84, `filelock` 3 → 4).
- Trace export to Tempo, and dashboards or alerts keyed on span attribute names: HTTP semantic conventions changed across these
  OpenTelemetry versions (for example `http.target`).
- `hyper-agents-gate2-e2e` did not run (path filter) on either PR.
- Authlib 1.6 → 1.9 and GitPython 3.1 → 3.2: nothing in `backend/app` imports them directly, so CI cannot show they still work; check
  what pulls them in.
- The audit workflow uses Python 3.11 while the images run 3.12, which can resolve differently.

## Files

| File | What it is |
|---|---|
| `requirements.baseline.txt` | The runtime pins before the bumps |
| `requirements.candidateA.txt`, `A.diff` | Candidate A (what #704 applies) |
| `requirements.candidateB.txt`, `B.diff` | A plus the OpenTelemetry family together (the two PRs split this) |
| `targets.json`, `make_candidates.py` | Minimum safe version per vulnerable package, and the script that builds A and B |
| `otel-resolved.json`, `make_otel_only.py` | The OpenTelemetry set pip resolved together, and the script that applies only that |
| `audit-baseline.json`, `audit-candidateA.json`, `audit-candidateB.json` | pip-audit results for exact pins (accepted-risk list applied) |
| `smoke.old.txt`, `smoke.new.txt`, `smoke-run.log` | Pins and output of the old-vs-new OpenTelemetry test run |
| `dryrun-docker-baseline.log`, `dryrun-docker-candidate.log`, `run_dryrun_docker2.sh` | Resolver control (passes) and the OpenTelemetry conflict |
