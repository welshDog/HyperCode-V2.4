# MCP Tool Server Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close a real, currently-unmitigated-except-by-network-isolation authentication gap: every route on `stripe-mcp` and `broski-economy-mcp` (both standalone MCP tool servers) except `/health` must require a valid `Authorization: Bearer <token>` header before any handler logic — including DB access — runs.

**Architecture:** A small auth-check FastAPI dependency, duplicated (not shared — see spec's Context section for why) in each `server.py`, checked via `hmac.compare_digest` against a per-server secret env var. Every route gets `dependencies=[Depends(require_mcp_token)]` except `/health`. Fails closed: an unset/empty secret rejects every request rather than allowing a bypass.

**Tech Stack:** Python 3.13, FastAPI, pytest, stdlib `hmac` (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-08-15-mcp-tool-server-auth-design.md`

## Global Constraints

- Auth check must run before any DB connection is opened or tool logic executes.
- `hmac.compare_digest` for the token comparison — never `==`.
- Separate secret env var per server: `STRIPE_MCP_AUTH_TOKEN` for stripe-mcp, `BROSKI_ECONOMY_MCP_AUTH_TOKEN` for broski-economy-mcp. Never shared.
- `/health` stays open on both servers — no auth required.
- Missing header → `401`. Wrong/empty token → `403`.
- No new dependencies (stdlib `hmac` only).
- This plan does not change Docker networking, compose port bindings, or make either server externally reachable — auth only.

---

### Task 1: `stripe-mcp` authentication

**Files:**
- Modify: `agents/stripe-mcp/server.py`
- Modify: `docker-compose.stripe-mcp.yml`
- Modify: `agents/stripe-mcp/README.md`
- Test: `backend/tests/test_stripe_mcp_auth.py`

**Interfaces:**
- Produces: `require_mcp_token` FastAPI dependency in `stripe-mcp/server.py`, gating every route except `/health`. No interface consumed by Task 2 — the two tasks are independent (same shape, separate services).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_stripe_mcp_auth.py`:

```python
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stripe_mcp_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_MCP_AUTH_TOKEN", "test-secret-token")
    mod = _load_module(
        "hc_stripe_mcp_mod",
        Path(__file__).resolve().parents[2] / "agents" / "stripe-mcp" / "server.py",
    )
    return mod.app


def test_health_requires_no_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_well_known_mcp_requires_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/.well-known/mcp")
    assert resp.status_code == 401


def test_resource_plans_requires_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/mcp/resources/stripe://plans")
    assert resp.status_code == 401


def test_tool_call_missing_auth_header_returns_401(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post("/mcp/tools/nonexistent_tool", json={})
    assert resp.status_code == 401


def test_tool_call_wrong_token_returns_403(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_tool_call_valid_token_reaches_dispatcher(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # 404 (unknown tool) proves auth passed — the request reached the
    # dispatcher's own unknown-tool check, unchanged by this fix.
    assert resp.status_code == 404
```

All three tool-call tests deliberately target `nonexistent_tool`, not a real
tool name — the auth guard doesn't care which tool was requested, and this
keeps every test in this file free of any real DB/Stripe network call.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_stripe_mcp_auth.py -v`

Expected: 4 of 6 FAIL — `test_health_requires_no_auth` already passes (route
is currently open, correctly), and `test_tool_call_valid_token_reaches_dispatcher`
already passes too (nothing blocks the request today, so it already reaches
the dispatcher's 404). The other four fail because every route currently
returns `200` (or, for the tool-call ones, `404` from the dispatcher) instead
of the `401`/`403` these tests expect — there is no auth check yet.

- [ ] **Step 3: Add the auth dependency and gate every non-health route**

In `agents/stripe-mcp/server.py`, add near the top of the file, after the
existing `stripe.api_key = STRIPE_SECRET_KEY` config block:

```python
import hmac
from fastapi import Header
```

(Add `Header` to the existing `from fastapi import FastAPI, Request, HTTPException` line rather than a separate import — result: `from fastapi import FastAPI, Request, HTTPException, Header`.)

Then, directly above the `# ---------- MCP Server ----------` section:

```python
async def require_mcp_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <token> required")
    token = authorization.removeprefix("Bearer ").strip()
    expected = os.environ.get("STRIPE_MCP_AUTH_TOKEN", "")
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid token")
```

Then add `dependencies=[Depends(require_mcp_token)]` to every route decorator
except `/health`. This also needs `Depends` added to the fastapi import:
`from fastapi import FastAPI, Request, HTTPException, Header, Depends`.

```python
@app.get("/.well-known/mcp", dependencies=[Depends(require_mcp_token)])
async def mcp_discovery():
    return {"tools": TOOLS, "resources": RESOURCES}


@app.post("/mcp/tools/{tool_name}", dependencies=[Depends(require_mcp_token)])
async def call_tool(tool_name: str, request: Request):
    ...  # body unchanged


@app.get("/mcp/resources/stripe://subscription/{user_id}", dependencies=[Depends(require_mcp_token)])
async def resource_subscription(user_id: str):
    return await get_subscription_resource(user_id)


@app.get("/mcp/resources/stripe://plans", dependencies=[Depends(require_mcp_token)])
async def resource_plans():
    return await get_plans_resource()
```

`@app.get("/health")` is not touched — stays open, no `dependencies=`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_stripe_mcp_auth.py -v`
Expected: PASS — all 6 tests green.

- [ ] **Step 5: Document the new env var**

In `docker-compose.stripe-mcp.yml`, add to the `environment:` block (after
`STRIPE_CANCEL_URL`):

```yaml
      - STRIPE_MCP_AUTH_TOKEN=${STRIPE_MCP_AUTH_TOKEN}
```

In `agents/stripe-mcp/README.md`, add a new section between `## Architecture`
and `## Deployment`:

```markdown
## Authentication

Every route except `/health` requires `Authorization: Bearer <token>`,
checked against the `STRIPE_MCP_AUTH_TOKEN` env var (constant-time
comparison). Missing header → `401`. Wrong token → `403`. An unset or
empty `STRIPE_MCP_AUTH_TOKEN` rejects every request — the server fails
closed, never open, on misconfiguration.
```

- [ ] **Step 6: Commit**

```bash
git add agents/stripe-mcp/server.py agents/stripe-mcp/README.md docker-compose.stripe-mcp.yml backend/tests/test_stripe_mcp_auth.py
git commit -m "feat: add Bearer token auth to stripe-mcp server"
```

---

### Task 2: `broski-economy-mcp` authentication

**Files:**
- Modify: `agents/broski-economy-mcp/server.py`
- Modify: `docker-compose.broski-economy-mcp.yml`
- Modify: `agents/broski-economy-mcp/README.md`
- Test: `backend/tests/test_broski_economy_mcp_auth.py`

**Interfaces:**
- Produces: `require_mcp_token` FastAPI dependency in `broski-economy-mcp/server.py`, gating every route except `/health`. Independent of Task 1 (same shape, separate service, separate secret).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_broski_economy_mcp_auth.py`:

```python
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def broski_economy_mcp_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("BROSKI_ECONOMY_MCP_AUTH_TOKEN", "test-secret-token")
    mod = _load_module(
        "hc_broski_economy_mcp_mod",
        Path(__file__).resolve().parents[2] / "agents" / "broski-economy-mcp" / "server.py",
    )
    return mod.app


def test_health_requires_no_auth(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_well_known_mcp_requires_auth(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.get("/.well-known/mcp")
    assert resp.status_code == 401


def test_tool_call_missing_auth_header_returns_401(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post("/mcp/tools/nonexistent_tool", json={})
    assert resp.status_code == 401


def test_tool_call_wrong_token_returns_403(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_tool_call_valid_token_reaches_dispatcher(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # NOT 404. This file's unknown-tool branch (line ~239-240) does
    # `return {"error": ...}, 404` — a plain tuple, which FastAPI does not
    # special-case into an HTTP 404; it serializes as a 200 with a
    # malformed JSON-array body `[{"error":...}, 404]`. Confirmed
    # empirically before this task started. That's a pre-existing bug in
    # the dispatcher, unrelated to auth and out of scope for this task —
    # do not fix it here. This test only needs to prove the valid token
    # reached the dispatcher at all (i.e. wasn't blocked by auth), so it
    # asserts the actual current behavior, not the status code a correct
    # implementation would return.
    assert resp.status_code == 200
    assert "Unknown tool" in resp.text
```

Note: this file deliberately does NOT include a resource-route auth test
(unlike stripe-mcp's `test_resource_plans_requires_auth`). Every resource
route on this server (`get_balance_resource`, `get_transactions_resource`)
touches the DB directly with no DB-free route available — testing one
pre-fix would attempt a real connection to the dummy `DATABASE_URL` and
produce a slow/flaky failure instead of a clean one. The `/.well-known/mcp`
and tool-call tests already prove the auth dependency works correctly;
Step 3 applies the identical `dependencies=[Depends(require_mcp_token)]`
to the resource routes too, and that symmetry is verified by code review
in Step 4, not by an additional DB-touching test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_broski_economy_mcp_auth.py -v`

Expected: 3 of 5 FAIL (`test_well_known_mcp_requires_auth`,
`test_tool_call_missing_auth_header_returns_401`,
`test_tool_call_wrong_token_returns_403`) — same reasoning as Task 1:
every route is currently open, so these get `200` instead of the
`401`/`403` expected. `test_health_requires_no_auth` and
`test_tool_call_valid_token_reaches_dispatcher` already pass (the latter
asserts today's actual — buggy but out-of-scope — `200` response, not a
`404`; see the comment in that test).

- [ ] **Step 3: Add the auth dependency and gate every non-health route**

In `agents/broski-economy-mcp/server.py`, add `import hmac` near the top
(after the existing `import json` line).

Add `Header` and `Depends` to the existing fastapi import line — currently
`from fastapi import FastAPI, Request, Response` (line 141) — becomes:
`from fastapi import FastAPI, Request, Response, Header, Depends, HTTPException`
(this file doesn't currently import `HTTPException` — it's needed now for
the auth dependency to raise on failure).

Add, directly above the `TOOLS = {` definition:

```python
async def require_mcp_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <token> required")
    token = authorization.removeprefix("Bearer ").strip()
    expected = os.environ.get("BROSKI_ECONOMY_MCP_AUTH_TOKEN", "")
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid token")
```

Then gate every route except `/health`:

```python
@app.get("/.well-known/mcp", dependencies=[Depends(require_mcp_token)])
async def mcp_discovery():
    ...  # body unchanged


@app.post("/mcp/tools/{tool_name}", dependencies=[Depends(require_mcp_token)])
async def call_tool(tool_name: str, request: Request):
    ...  # body unchanged


@app.get("/mcp/resources/broski://balance/{discord_id}", dependencies=[Depends(require_mcp_token)])
async def resource_balance(discord_id: str):
    ...  # body unchanged


@app.get("/mcp/resources/broski://transactions/{discord_id}", dependencies=[Depends(require_mcp_token)])
async def resource_transactions(discord_id: str, limit: int = 10):
    ...  # body unchanged
```

`@app.get("/health")` (line 200) is not touched.

- [ ] **Step 4: Run tests to verify they pass, and manually confirm resource-route gating**

Run: `cd HyperCode-V2.4 && python -m pytest backend/tests/test_broski_economy_mcp_auth.py -v`
Expected: PASS — all 5 tests green.

Then re-read the diff on `resource_balance` and `resource_transactions` to
confirm both carry `dependencies=[Depends(require_mcp_token)]` — this is
the symmetry check the Step 1 note called out, done by inspection since a
DB-touching test isn't worth the flakiness here.

- [ ] **Step 5: Document the new env var**

In `docker-compose.broski-economy-mcp.yml`, add to the `environment:` block
(after `DATABASE_URL`):

```yaml
      - BROSKI_ECONOMY_MCP_AUTH_TOKEN=${BROSKI_ECONOMY_MCP_AUTH_TOKEN}
```

In `agents/broski-economy-mcp/README.md`, add a new section between
`## Architecture` and `## Deployment`:

```markdown
## Authentication

Every route except `/health` requires `Authorization: Bearer <token>`,
checked against the `BROSKI_ECONOMY_MCP_AUTH_TOKEN` env var (constant-time
comparison). Missing header → `401`. Wrong token → `403`. An unset or
empty `BROSKI_ECONOMY_MCP_AUTH_TOKEN` rejects every request — the server
fails closed, never open, on misconfiguration.
```

- [ ] **Step 6: Commit**

```bash
git add agents/broski-economy-mcp/server.py agents/broski-economy-mcp/README.md docker-compose.broski-economy-mcp.yml backend/tests/test_broski_economy_mcp_auth.py
git commit -m "feat: add Bearer token auth to broski-economy-mcp server"
```

---

## Self-Review Notes

- **Spec coverage:** auth-check function + `hmac.compare_digest` (both
  tasks' Step 3), separate secret per server (`STRIPE_MCP_AUTH_TOKEN` /
  `BROSKI_ECONOMY_MCP_AUTH_TOKEN`), every route except `/health` gated
  (including resource routes, not just tools), fail-closed on
  misconfiguration (the `not expected` check), README + compose
  documentation (Step 5 of both tasks). No spec section without a task.
  External exposure and the full `agent_api_keys` pattern are explicitly
  Out of Scope in the spec — no task attempts either.
- **Placeholder scan:** no TBD/TODO. The two `...  # body unchanged`
  markers in Task 2 Step 3 refer to route bodies that are verbatim
  unchanged from the existing file (already fully shown in this plan's
  context section and the spec) — not a placeholder for new logic, just
  avoiding repeating unchanged code a second time in the same document.
- **Type consistency:** `require_mcp_token` has the identical signature
  and behavior in both tasks (only the env var name differs), matching
  the spec's "duplicated, not shared" decision. Both raise `HTTPException`
  with the same status codes and detail message shape.
