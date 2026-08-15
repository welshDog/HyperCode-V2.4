# MCP Tool Server Authentication — Design

## Context & Constraints

- `agents/stripe-mcp/server.py` and `agents/broski-economy-mcp/server.py`
  are standalone FastAPI microservices (own directory, Dockerfile,
  `requirements.txt` — not part of the main `backend/app` service) exposing
  MCP-style tool-call endpoints.
- **Both currently have zero application-level authentication.** Every
  route — `/.well-known/mcp`, `POST /mcp/tools/{tool_name}`, and every
  `/mcp/resources/*` — is open to any caller that can reach the container.
  Their only protection today is Docker network isolation
  (`docker-compose.mcp-gateway.yml` binds everything to `127.0.0.1`; these
  two servers aren't in that file at all — `docker-compose.stripe-mcp.yml`
  / `docker-compose.broski-economy-mcp.yml` rely on the default Docker
  network being unreachable from outside the host).
- `broski-economy-mcp`'s `award_tokens`/`spend_tokens` tools wrap
  `SECURITY DEFINER` SQL functions with no caller-identity check — an
  unauthenticated caller who reaches the container can mint unlimited
  BROski$ to any `discord_id`, or drain any user's balance via
  `spend_tokens` with an arbitrary `discord_id`. `stripe-mcp`'s
  `create_checkout` accepts an arbitrary `user_id` as
  `client_reference_id` with no verification it's the caller's own
  identity — lower severity (doesn't move money directly) but still an
  unverified-identity gap.
- This spec fixes authentication only. External network exposure (making
  either server reachable outside the host) is explicitly a separate,
  later decision — Out of Scope below.
- The codebase already has a mature per-agent-key auth pattern
  (`backend/app/middleware/agent_auth.py`'s `require_agent_key` — hashed
  keys in a DB table, per-agent Redis rate limiting) but it lives inside
  the main `backend/app` service and depends on Postgres tables + Redis
  neither of these two standalone servers currently touch for auth
  purposes. Replicating it here would add new DB/Redis dependencies to
  two small services for what is currently a small number of trusted
  internal callers — rejected as disproportionate for v1 (see Out of
  Scope).
- `agents/shared/` exists as a directory but is not wired into either
  server's Docker build (`docker-compose.broski-economy-mcp.yml`'s build
  `context: ./agents/broski-economy-mcp`; the Dockerfile only
  `COPY requirements.txt .` and `COPY server.py .`). Using it here would
  require changing both build contexts and Dockerfiles to share ~15 lines
  of code — rejected; the auth-check function is duplicated directly in
  each `server.py` instead.

## Goal

Every route on both servers except `/health` requires a valid
`Authorization: Bearer <token>` header, checked against a per-server
secret env var, before any handler logic (including DB access) runs.
Missing header → `401`. Wrong token → `403`. Valid token → request
proceeds exactly as today.

## Design

### 1. Per-server auth-check function (duplicated, not shared)

Added directly to each `server.py`, near the top after the existing
config/env-var block:

```python
import hmac
from fastapi import Header

async def require_mcp_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <token> required")
    token = authorization.removeprefix("Bearer ").strip()
    expected = os.environ.get("<SECRET_ENV_VAR>", "")
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid token")
```

`<SECRET_ENV_VAR>` is `STRIPE_MCP_AUTH_TOKEN` in `stripe-mcp/server.py`,
`BROSKI_ECONOMY_MCP_AUTH_TOKEN` in `broski-economy-mcp/server.py` — one
copy of the function per file, with that one string substituted. Using
`hmac.compare_digest` (stdlib) for constant-time comparison, not `==`.

An empty/unset secret env var means every token is rejected (`expected`
is `""`, `compare_digest` against an empty expected value never matches a
non-empty token, and an empty token is already caught by the
`not authorization` check) — the server fails closed if misconfigured,
never open.

### 2. Separate secret per server

`STRIPE_MCP_AUTH_TOKEN` and `BROSKI_ECONOMY_MCP_AUTH_TOKEN` are
independent secrets. Matches this codebase's existing convention
(`SHOP_SYNC_SECRET` / `COURSE_SYNC_SECRET` are already separate
per-purpose secrets, not shared) — a leak of one doesn't compromise the
other.

### 3. Route gating — every route except `/health`

Add `dependencies=[Depends(require_mcp_token)]` to every route decorator
except `@app.get("/health")`. This includes the `/mcp/resources/*`
routes, not just `/mcp/tools/{tool_name}` and `/.well-known/mcp` — a
user's Stripe subscription status and BROski$ balance/transaction history
are sensitive reads, not just the mutating tools.

`stripe-mcp/server.py` routes to gate: `/.well-known/mcp` (line 253),
`/mcp/tools/{tool_name}` (258), `/mcp/resources/stripe://subscription/{user_id}`
(280), `/mcp/resources/stripe://plans` (285). `/health` (248) stays open.

`broski-economy-mcp/server.py` routes to gate: `/.well-known/mcp` (205),
`/mcp/tools/{tool_name}` (217), `/mcp/resources/broski://balance/{discord_id}`
(245), `/mcp/resources/broski://transactions/{discord_id}` (254).
`/health` (200) stays open.

## API Behaviour Summary

| Request | Result |
|---|---|
| No `Authorization` header | `401`, `{"detail": "Authorization: Bearer <token> required"}` |
| `Authorization` header present, wrong/empty token | `403`, `{"detail": "Invalid token"}` |
| Valid token | Request proceeds to the handler exactly as today |
| `GET /health` | Always `200`, no auth required (matches every other service in this codebase — `agent_registry.py`'s roster, `hyperflow_runner.py`, etc. all leave `/health` open) |

## Error Handling

Auth failure raises before any DB connection is opened or any tool logic
runs — `get_db_pool()` / `stripe.checkout.Session.create()` /
`award_tokens()` etc. are never reached on a 401 or 403. Fails closed: a
missing or empty secret env var rejects every request rather than
allowing an unauthenticated bypass.

## Testing Plan

New files, following the precedent already established by
`backend/tests/test_agent_http_auth_enforcement.py` (loads a standalone
`agents/*/*.py` script via `importlib.util.spec_from_file_location`,
drives it with `starlette.testclient.TestClient` directly — no need for
the full `backend` app or its `client` fixture):

**`backend/tests/test_stripe_mcp_auth.py`:**
- No `Authorization` header on `/mcp/tools/get_subscription` → `401`.
- Wrong token → `403`.
- Valid token, unknown tool name → `404` (proves the request reached the
  dispatcher — i.e. auth passed — without needing to mock `asyncpg` or
  Stripe).
- `/.well-known/mcp` and `/mcp/resources/stripe://plans` also `401`
  without a header.
- `/health` returns `200` with no `Authorization` header at all.

**`backend/tests/test_broski_economy_mcp_auth.py`:** same shape, against
`broski-economy-mcp/server.py`'s routes.

Both `stripe-mcp/server.py` and `broski-economy-mcp/server.py` raise
`RuntimeError` at import time if `DATABASE_URL` (and, for stripe-mcp,
`STRIPE_SECRET_KEY`) aren't set — tests must `monkeypatch.setenv` dummy
values for these (and the new `*_MCP_AUTH_TOKEN` var) before importing the
module. No real Postgres or Stripe connection is needed since these tests
never reach the DB/Stripe-touching code paths.

## Out of Scope (future, not this spec)

- External network exposure of either server — a separate, later
  decision once this auth fix is live. Nothing in this spec changes
  Docker networking or compose port bindings.
- The full `agent_api_keys` hashed-key + per-agent-rate-limit pattern
  (per-caller keys, revocation, audit trail) — deferred until there's a
  real need for more than one trusted caller identity per server. A
  single shared secret per server is proportionate for the current
  (internal-only) caller set.
- Wiring `agents/shared/` into either server's Docker build — not needed
  while the shared code in question is ~15 duplicated lines.

## Rollout Order

1. Add `require_mcp_token` + gate every non-`/health` route in
   `stripe-mcp/server.py`.
2. Write `backend/tests/test_stripe_mcp_auth.py`.
3. Repeat 1-2 for `broski-economy-mcp/server.py`.
4. Document the two new env vars (`STRIPE_MCP_AUTH_TOKEN`,
   `BROSKI_ECONOMY_MCP_AUTH_TOKEN`) in each server's `README.md` and in
   the relevant `docker-compose.*.yml` file's `environment:` block
   (value sourced from secrets, never committed).
