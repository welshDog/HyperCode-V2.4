Date: Wednesday 8 April 2026 | Branch: main | Repo: github.com/welshDog/HyperCode-V2.4

Executive Summary
HyperCode-V2.4 is a large, multi-language monorepo covering a FastAPI backend, Next.js dashboard, Go quantum-compiler, Celery workers, Docker Compose infra, and an E2E Playwright test suite. The stack is broadly functional — Docker services are healthy, the dashboard passes all 58 unit tests, and the Go module compiles cleanly. However, two Python bugs cause 5 test failures, critical committed secrets require immediate rotation, and E2E tests are broken due to a route/selector mismatch. This report documents every finding, root cause, and an ordered remediation plan.

1. Repository Structure
Layer	Technology	Location
Backend API	Python 3.11 · FastAPI	backend/app/
Agent Brain	Perplexity AI → Ollama → OpenRouter	backend/app/agents/brain.py
Crypto / Sync	AES-256-GCM · Hypersync	backend/app/core/hypersync.py
Dashboard	Next.js / React · TypeScript	agents/dashboard/
Workers	Celery 5.6	backend/app/workers/
Infra	Docker Compose · Redis · PostgreSQL · MinIO · Chroma	docker-compose.yml
Observability	Prometheus + Grafana	localhost:9090 / localhost:3001
E2E Tests	Playwright (Chromium)	tests/e2e/
Go Module	quantum-compiler	quantum-compiler/
Notable config files present: .pre-commit-config.yaml, .secrets.baseline, .husky/, CLAUDE.md, .mcp.json — showing strong DevOps intention.

2. Automated Test Results
2.1 Python Backend (pytest)
Metric	Result
Passed	136
Failed	5
Skipped	6 (env-gated: Redis/Postgres/Ollama)
Coverage	54%
Runtime	~15 min 12 sec
Root Cause A — _sha256_hex type contract mismatch

The function signature in backend/app/core/hypersync.py is:

python
def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
In the rate-limiting code path, the function is called with a plain Python str instead of bytes. This raises a TypeError at runtime. The fix is a one-liner defensive guard:

python
def _sha256_hex(raw: bytes | str) -> str:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
Affected test logs: pytest-hypersync.log, pytest-rate-limit.log. 3 of the 5 failures trace to this.

Root Cause B — Brain recall_context fallback removed

backend/app/agents/brain.py line ~62 currently returns "" when RAG fails:

python
# 2. Fallback to Recent Files (Temporal)
# Privacy-first: do not pull arbitrary bucket content into prompts by default.
return ""
A test (test_recall_context_falls_back_to_storage_on_rag_failure) expects a file-based fallback result. The implementation was intentionally changed to privacy-first. Decision required: either update the test to assert "" (recommended — aligns with privacy design), or add a BRAIN_ALLOW_FILE_FALLBACK=true env flag to gate the old behaviour.

Affected test log: pytest-brain.log. 2 of the 5 failures trace to this.

2.2 Dashboard Unit Tests (Vitest)
Metric	Result
Test files	15
Tests passed	58 ✅
Duration	62.60 sec
ESLint	Clean ✅
TypeScript tsc --noEmit	Clean ✅
Note: Multiple act(...) warnings present in HyperShellLayout tests. These are cosmetic today but can mask real async state update bugs if ignored long-term. Recommend wrapping async interactions in act() in those test files.

2.3 Go Module (quantum-compiler)
Metric	Result
go test ./...	Passed ✅
Coverage	6.7% ⚠️
The module compiles and tests pass, but 6.7% coverage means almost the entire quantum-compiler logic is untested. Any refactor or dependency bump carries high regression risk. Recommend targeting 40%+ coverage as a short-term goal.

2.4 E2E Tests (Playwright — Chromium)
Metric	Result
Passed	2
Failed	5
Runtime	~5 min 24 sec
Failure Pattern A — shell.spec.ts selector timeout

page.goto('/') navigates, then waitForSelector('[data-testid="hyper-shell"]') times out. The HyperShell component is either not mounted at /, is behind a feature flag, or the data-testid attribute was removed during a refactor. Fix: align baseURL and selector in the spec with the actual current route.

Failure Pattern B — accessibility.spec.ts critical violations

axe-core reports critical WCAG violations. These are real accessibility bugs, not test noise. Common causes include: missing aria-label on icon-only buttons, broken heading hierarchy, insufficient colour contrast, or form inputs without associated <label> elements.

3. Static Analysis
3.1 Ruff (Python linter)
16 issues found. Highest-priority items:

File	Issue	Severity
backend/app/api/v1/endpoints/orchestrator.py	HTTPException used but not imported	🔴 Runtime crash
backend/app/main.py	Unused imports + E402 import order	🟡 Hygiene
backend/app/core/config.py	Unused imports + E402 import order	🟡 Hygiene
The HTTPException missing import will cause a NameError at runtime on any request that hits an error path in orchestrator.py. Fix: add from fastapi import HTTPException at the top of that file.

3.2 npm Audit
Package scope	Vulnerabilities
Root workspace	0 ✅
agents/dashboard	1 moderate (Next.js advisory range)
The Next.js moderate advisory in the dashboard does not affect production builds (only dev tooling), but the recommended upgrade falls outside the currently pinned version range. Evaluate the upgrade path against any breaking changes in the Next.js release notes.

4. Infrastructure Health
4.1 Docker Compose — Service Status
All core services reported healthy at time of scan. Key resource readings:

Service	CPU	RAM	Limit	Status
hypercode-core	Low	~360 MiB	1 GiB (35%)	✅ Healthy
hypercode-dashboard	~44% spike	~85 MiB	—	✅ Running
hypercode-ollama	~17%	~35 MiB	—	✅ Running
prometheus	~11%	~134 MiB	—	✅ Running
redis	Low	Low	—	✅ Running
postgres	Low	Low	—	✅ Running
minio	Low	Low	—	✅ Running
Chroma health endpoint returned non-OK — the probe was using the wrong path. Verify the correct Chroma health URL (/api/v1/heartbeat may need to be /api/v2/heartbeat depending on version).

4.2 Portability Risk
Docker Compose uses absolute Windows paths for bind-mounted volumes (e.g., H:/HyperStation zone/HyperCode/volumes/**). This means the compose file cannot be deployed on any machine that isn't the specific Windows host. For CI or cloud deployment, these should be replaced with named Docker volumes or path-interpolated environment variables.

5. Security Findings
🔴 Critical — Act Immediately
1. Committed SSH Private Key

An SSH private key (id_ed25519) is present inside volumes/ollama/. If this path is within the Git-tracked workspace, the private key has been committed to version control. Assume this key is compromised.

Actions required:

Immediately revoke and rotate the SSH key pair on all systems it authenticates with

Remove the file: git rm --cached volumes/ollama/id_ed25519

Add the path to .gitignore

Run git filter-repo or BFG Repo Cleaner to purge it from Git history

2. Committed Database Backups

Three database files have been committed to the repository:

docs/archive/backups/production_backup.sql

docs/archive/backups/postgres/backup_20260207_183459.sql

agents/broski-bot/database/broski_main.db

These almost certainly contain database credentials, API tokens, user PII, or other sensitive data embedded in the SQL schema or rows.

Actions required:

Rotate ALL credentials that appear anywhere in those backup files

Remove the files from the repository with git rm

Purge from Git history using git filter-repo --path <file> --invert-paths

Add *.sql, *.db patterns to .gitignore

🔴 High — Fix This Week
3. Docker Socket Exposure

The Docker Compose file includes patterns that expose the host Docker socket to containers. A compromised container that has access to the Docker socket can escape to the host and gain full root-equivalent access to the machine.

Fix: Use a socket proxy (e.g., linuxserver/socket-proxy) with a strict allowlist of Docker API endpoints, rather than exposing the raw socket.

4. Unauthenticated Telemetry / WebSocket Endpoints

The WebSocket broadcasters under backend/app/ws/ (agents broadcaster, metrics broadcaster) appear to emit real-time data without requiring authentication. Any client that can reach the service can subscribe to live agent state, metrics, and log streams.

Fix: Add token or session-based authentication middleware to all WebSocket upgrade paths.

5. IDOR in Dashboard Execute Path

In backend/app/api/v1/endpoints/dashboard.py, project_id=1 is hardcoded. Any authenticated user can trigger execution in Project 1's context regardless of their actual project membership. This is a textbook Insecure Direct Object Reference (IDOR) vulnerability.

Fix: Resolve project_id from the authenticated user's session/token, and add authorisation checks to verify the user is a member of the requested project.

6. Performance Bottlenecks
Issue	File(s)	Impact
Redis KEYS scan (O(N) keyspace scan, blocks Redis)	agents_broadcaster.py, metrics_broadcaster.py	High — degrades linearly as keyspace grows
Per-client polling loops (work scales with client count)	Same WS broadcasters	High — CPU grows with connected clients
Sync DB calls inside async def endpoints	tasks.py, routes/tasks.py	Medium — blocks the FastAPI event loop
Redis KEYS fix: Replace with SCAN (cursor-based, non-blocking) or better — maintain an agent index in a Redis ZSET or SET and perform a single SMEMBERS/ZRANGE per broadcast cycle.

Per-client loop fix: Run a single background task that emits a snapshot to all clients on a timer, rather than one loop per connected client.

Async DB fix: Use asyncpg-backed SQLAlchemy async sessions, or move synchronous DB calls to a thread pool with run_in_executor.

7. Ordered Remediation Plan
P0 — Stop Active Security Bleed (Today)
Revoke the SSH key from volumes/ollama/id_ed25519 on all systems

Run git rm + git filter-repo to purge key from history

Rotate every credential that appears in the committed SQL/DB backup files

Remove the backup files from history with git filter-repo

Update .gitignore with *.pem, *.key, id_ed25519*, *.sql, *.db

P1 — Restore Backend Test Green (This Sprint)
Fix _sha256_hex to accept str | bytes (one-liner change in hypersync.py)

Either: update test_recall_context_falls_back_to_storage_on_rag_failure to assert "" OR add BRAIN_ALLOW_FILE_FALLBACK config flag

Add from fastapi import HTTPException to orchestrator.py (prevents runtime NameError)

P2 — Stabilise E2E (Next Sprint)
Audit current routing — find what route HyperShell actually lives at and update shell.spec.ts baseURL / goto() / selector

Fix the axe-core accessibility violations surfaced by accessibility.spec.ts (aria-labels, headings, contrast)

P3 — Security Architecture (Next 2 Weeks)
Add auth middleware to all WebSocket upgrade paths in backend/app/ws/

Replace Docker socket bind-mount with a socket proxy + allowlist

Fix IDOR: derive project_id from auth context, not hardcoded value in dashboard.py

P4 — Scale & Performance (This Month)
Replace KEYS with SCAN or ZSET index in both WS broadcasters

Move per-client polling to a single shared broadcast task

Migrate synchronous DB calls in tasks.py / routes/tasks.py to async

P5 — Hygiene (Ongoing)
Resolve remaining 13 Ruff warnings (unused imports, E402 ordering)

Wrap HyperShellLayout Vitest async interactions in act() to clear warnings

Evaluate Next.js upgrade to resolve the moderate npm advisory

Grow Go quantum-compiler test coverage from 6.7% toward 40%+

8. Health Score Summary
Domain	Score	Status
Backend tests	136/141 passing	🟡 5 failures (fixable)
Dashboard tests	58/58 passing	✅ Green
Go tests	Pass	✅ Green
E2E tests	2/7 passing	🔴 Broken
Linting	16 issues	🟡 1 runtime-critical
Security	Critical issues present	🔴 Immediate action required
Infra / Docker	All services healthy	✅ Green
Performance	3 known bottlenecks	🟡 Fine at current scale
Code coverage (Python)	54%	🟡 Acceptable, improve to 70%+
Code coverage (Go)	6.7%	🔴 Too low
Report generated: 8 April 2026. Based on live repo scan of github.com/welshDog/HyperCode-V2.4 and local test-results artifacts from the automated CI sweep.