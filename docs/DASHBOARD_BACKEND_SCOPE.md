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

## ⚠️ Tech debt left behind

`mcp-rest-adapter` is currently a **`docker run` container, not compose-managed**.
It has `--restart unless-stopped` so it survives reboots, but a
`docker compose … up -d` will not know about it.

`docker-compose.mcp-gateway.yml` cannot cleanly merge into the main stack —
`mcp-gateway` is defined both there and via `docker-compose.agents.yml`, so
`-f docker-compose.yml -f docker-compose.mcp-gateway.yml` doubles list fields
(Sacred Rule #21). Proper fix, a follow-up:

- Add a lean `mcp-rest-adapter`-only service to a compose file that the root
  `docker-compose.yml` already `include:`s (e.g. `docker-compose.agents.yml`), OR
- De-dupe the `mcp-gateway` definition so `docker-compose.mcp-gateway.yml` can
  be safely included.

Env keys note: `MCP_GATEWAY_API_KEY` lives in **`.env.mcp`**, not `.env`.

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

## ⚠️ Real follow-up found — adapter ↔ gateway transport mismatch

`mcp-rest-adapter`'s `app.py` speaks the **old MCP SSE transport** (`GET /sse` →
`event: endpoint` → POST to a session URL, `protocolVersion 2024-11-05`).

The running `docker/mcp-gateway:latest` speaks the **newer Streamable HTTP
transport**: `:8820/sse` 307-redirects to `/mcp`, and `/mcp` rejects plain GETs
with `400 Bad Request: GET requires an Mcp-Session-Id header`.

Result — what works vs not:
- ✅ `filesystem:list_directory` under `/workspace` — adapter serves this
  **locally** (`_local_list_directory`), no gateway needed → IDE file-tree works
- ✅ `/api/mcp/health` — trivial, no gateway → MCP tab works
- ❌ `/tools/discover` — needs gateway → **HTTP 500** (httpx `HTTPStatusError`
  on the unfollowed 307)
- ❌ `filesystem:read_file` → IDE file *opening* — needs gateway → broken
- ❌ any real MCP tool call beyond local filesystem listing

**Fix (follow-up):** rewrite `services/mcp-rest-adapter/app.py`'s `_jsonrpc` to
speak Streamable HTTP — POST `initialize` → capture `Mcp-Session-Id` → reuse it
on subsequent POSTs. Not a config tweak; the SSE handshake code goes away.

## Genuine remaining dashboard work

1. ✅ **Browser-verify all 5 tabs** — DONE (table above).
2. **Adapter ↔ gateway transport rewrite** — Streamable HTTP (above). Unblocks
   IDE file-open + real MCP tool calls.
3. **Mission tab** shows nothing without a login token (`useTasks` reads
   `localStorage.token`; Core `/api/v1/tasks` is auth-gated). Decide: dashboard
   login flow, or a public read endpoint like `/agents/status`.
4. **Compose-manage `mcp-rest-adapter`** (tech debt above).
5. `DASHBOARD_UPGRADE_COMPONENTS/` staging prototype is dead — the live
   dashboard already does everything it sketched. Consider deleting it to stop
   future audits tripping over it.
