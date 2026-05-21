# 🔌 Dashboard Backend — Scope (CORRECTED)

> First scoped 2026-05-21 — **then rewritten the same day** after auditing the
> *live* dashboard. The first version was wrong: it scoped the abandoned
> `DASHBOARD_UPGRADE_COMPONENTS/` staging prototype, not the deployed app.

---

## ⚠️ Correction — the session report was wrong about the dashboard

`SESSION_REPORT_2026-05-21.md` (Block 3 + NEXT SESSION #2) said the
IDE/Mission/Docker/MCP tabs are *"backend-blocked — 0/8 endpoints exist —
budget a focused day."*

**That was about the staging prototype `DASHBOARD_UPGRADE_COMPONENTS/`.**
It is NOT the deployed dashboard. The `hypercode-dashboard` image builds from
`agents/dashboard/` (`docker-compose.agents.yml:236` — `context: ./agents/dashboard`).

`agents/dashboard/` is a mature, fully-wired Next.js app. It has all 5 tab
pages, real view components, and its own Next.js API proxy-route layer
(`app/api/*/route.ts`) that forwards to Core and the agent services. There was
never an "8 endpoints to build" task here.

---

## Real state of the live dashboard (`agents/dashboard/`)

| Tab | Route | Data path | State |
|---|---|---|---|
| Agent Monitor | `app/agents` | `useAgentStatus` → Core `/api/v1/agents/status` | ✅ Live (Option B, May 21) |
| Mission | `app/mission` | `useTasks` → `/api/tasks` → Core `/api/v1/tasks` | ✅ Wired — needs a login token to show rows |
| IDE | `app/ide` → `IDEView` | `/api/orchestrator` (execute) + `/api/mcp/tools/call` (file tree) | ✅ Wired |
| Docker Zone | `app/docker-zone` | static `<iframe>` → `/hypercode-docker-dashboard.html` | ✅ Self-contained — never backend-blocked |
| MCP | `app/mcp` → `MCPGatewayView` | `/api/mcp/*` → `mcp-rest-adapter:8821` | ✅ **FIXED 2026-05-21** (see below) |

---

## The one real bug — and the fix shipped

`/api/mcp/*` and the IDE file-tree both proxy to `mcp-rest-adapter:8821`.
**That container was never running.** One missing container broke two tabs.

### Fix applied 2026-05-21

1. `docker-compose.mcp-gateway.yml` — corrected two stale values:
   - `MCP_WORKSPACE_SOURCE_PATH` → `…/HYPERFOCUSZONE/HperCore/…` (was old `HyperStation zone` path)
   - external network `name:` → `hypercode_agents_net` (was non-existent `hypercode_public_net`)
2. Built the image: `docker build -t mcp-rest-adapter:local ./services/mcp-rest-adapter`
3. Started it with `docker run` (compose-merge hit Sacred Rule #21 — `mcp-gateway`
   is double-defined → `security_opt items 0 and 1 are equal`):

   ```
   docker run -d --name mcp-rest-adapter --network hypercode_agents_net \
     -p 127.0.0.1:8821:8821 --restart unless-stopped \
     --add-host host.docker.internal:host-gateway \
     -e MCP_GATEWAY_BASE_URL=http://host.docker.internal:8820 \
     -e MCP_GATEWAY_SSE_URL=http://host.docker.internal:8820/sse \
     -e MCP_GATEWAY_AUTH_TOKEN=<MCP_GATEWAY_API_KEY from .env.mcp> \
     -e MCP_WORKSPACE_TARGET_PATH=/workspace \
     -e MCP_WORKSPACE_SOURCE_PATH=/run/desktop/mnt/host/h/HYPERFOCUSZONE/HperCore/HyperCode-V2.4 \
     -e MCP_LOCAL_WORKSPACE_ROOT=/workspace \
     -v <repo>:/workspace:ro  mcp-rest-adapter:local
   ```

### Verified

- `mcp-rest-adapter` container `Up`, uvicorn on `0.0.0.0:8821`
- `/health` → `{"status":"ok"}` from inside the adapter AND from the dashboard
  container via Docker DNS
- Dashboard `GET /api/mcp/health` → **HTTP 200** `{"status":"ok"}`
- `/mcp` tab page → HTTP 200

---

## ✅ RESOLVED 2026-05-21 — `mcp-rest-adapter` is now compose-managed

Was a standalone `docker run` container. Now a first-class service:

- **`docker-compose.agents.yml`** — added the `mcp-rest-adapter` service
  (`profile: agents`, on `agents-net`, talks to `mcp-gateway:8820` over Docker
  DNS, 256 MB cap, healthcheck, `cap_drop: ALL`). The root `docker-compose.yml`
  already `include:`s `agents.yml`, so it is part of the main stack.
- **`docker-compose.mcp-gateway.yml`** — the stale duplicate `mcp-rest-adapter`
  block removed (replaced with a pointer comment) so the two cannot drift.
- No secret needed: the live `mcp-gateway` runs `--servers=github` with **no
  auth**, so the adapter sends no token — `MCP_GATEWAY_API_KEY` / `.env.mcp` are
  no longer in the picture.

Start: `docker compose -f docker-compose.yml --profile agents up -d`
Verified: container labelled `project: hypercode-v24, service: mcp-rest-adapter`,
healthcheck `healthy`, `/api/mcp/health` + `/tools/discover` + file-read all 200.

---

## Verification sweep — 2026-05-21

All 5 tab pages + their data endpoints probed at `http://127.0.0.1:8088`.

| Tab | Page | Data path | Verdict |
|---|---|---|---|
| Agent Monitor | 200 | Core `/api/v1/agents/status` → 3 live agents (healer/core/celery) | ✅ WORKS |
| Mission | 200 | `/api/tasks` → `{tasks:[],total:0}` — empty, no login token | ✅ WORKS (needs login for rows) |
| IDE | 200 | file-tree dir-listing → real `/workspace` entries ✅; `/api/orchestrator` reachable | ⚠️ MOSTLY (file *open* broken — see below) |
| Docker Zone | 200 | static `/hypercode-docker-dashboard.html` → 200 | ✅ WORKS |
| MCP | 200 | `/api/mcp/health` → 200 (all `MCPGatewayView` uses) | ✅ WORKS |

**4/5 fully working; IDE mostly.** Every tab renders and its primary built-in
function works.

## ✅ RESOLVED 2026-05-21 — adapter ↔ gateway transport rewrite

Was: `mcp-rest-adapter`'s `app.py` spoke the **old MCP SSE transport** while
`docker/mcp-gateway:latest` speaks **Streamable HTTP** (`:8820/sse` → 307 →
`/mcp`; `/mcp` needs an `Mcp-Session-Id` header).

**Fix shipped** — `services/mcp-rest-adapter/app.py` rewritten:
- `_jsonrpc` now does the Streamable HTTP handshake: POST `initialize` →
  capture `Mcp-Session-Id` header → POST `notifications/initialized` → POST the
  real method → best-effort `DELETE` to terminate the session
- `_extract_jsonrpc_message` parses both `application/json` and
  `text/event-stream` POST responses
- endpoint resolution: new `MCP_GATEWAY_MCP_URL` env (compose updated); legacy
  `/sse` URLs auto-rewritten to `/mcp`
- the old SSE handshake (`_await_jsonrpc_response`, `event: endpoint`) is gone

**Filesystem note:** the gateway serves only GitHub tools (28) — no `filesystem`
server is running. So directory listing AND file reads are served **locally**
from the read-only `/workspace` bind mount. Added `_local_read_file` (mirrors
`_local_list_directory`) — 1 MB cap, UTF-8 only, path-sandboxed to the workspace.

**Verified** via the dashboard proxy:
- `/api/mcp/tools/discover` → 200 (28 real gateway tools through the handshake)
- `tools/call filesystem:list_directory` → 200 (real `/workspace` entries)
- `tools/call filesystem:read_file` → 200 (real file content) — **IDE file-open works**
- path-escape `../../../etc/passwd` → **403 Forbidden** (sandbox holds)

## Genuine remaining dashboard work

1. ✅ **Browser-verify all 5 tabs** — DONE.
2. ✅ **Adapter Streamable HTTP rewrite** — DONE (above). IDE fully unlocked.
3. **Mission tab** shows nothing without a login token (`useTasks` reads
   `localStorage.token`; Core `/api/v1/tasks` is auth-gated). Decide: dashboard
   login flow, or a public read endpoint like `/agents/status`.
4. ✅ **Compose-manage `mcp-rest-adapter`** — DONE (now in `agents.yml`).
5. `DASHBOARD_UPGRADE_COMPONENTS/` staging prototype is dead — the live
   dashboard already does everything it sketched. Consider deleting it to stop
   future audits tripping over it.
6. *(optional)* Bring up the `filesystem` / `postgres` MCP servers if the IDE
   ever needs gateway-backed file ops beyond the local `/workspace` mount.
