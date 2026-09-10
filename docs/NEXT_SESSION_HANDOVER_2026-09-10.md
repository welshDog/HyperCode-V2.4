# Next-session handover — 2026-09-10 (dashboard status panels: fleet registry + MCP gateway)

## 🎉 What shipped this session — pushed to `main` (evo-harness gate 26/26 green each)

Two dashboard status panels were showing red. Both fixed, verified live, committed.

### 1. Fleet registry panel — `agent-registry` :8077 (`d3181c9d`)

Mission Control's **"Fleet registry"** panel: `not reachable (is agent-registry running?)`.

- **Cause:** the `agent-registry` container didn't exist — **no image had ever been
  built on this box** (`hypercode-v24-agent-registry`); never started since the last
  full stack bring-up.
- **Fix:** `docker compose up -d agent-registry` from the repo root. The root
  `docker-compose.yml` already pulls in `docker-compose.registry.yml` via `include:` —
  run it **plain**, never `-f docker-compose.registry.yml` (that file declares
  `agents-net`/`data-net` as `external: true`; they only resolve when merged with
  `core.yml`'s concrete defs via the include — `-f` alone → external-net error +
  false orphan warnings). Build ~90s.
- **Verified:** container `healthy`, `127.0.0.1:8077` bound, `GET /health` →
  `{"status":"healthy","agents_tracked":42}`; `hypercode-dashboard` reaches
  `agent-registry:8077` over `agents-net`; dashboard `/api/fleet` → 200 with real
  data (`42 total · 7 healthy · 6 running · 13 down · 16 not_deployed`).
- Deps were already healthy: `redis`, `docker-socket-proxy`, `docker-socket-proxy-healer`.

### 2. MCP Gateway panel — `hypercode-mcp-server` :8823 (`acdd812b`)

Dashboard **"🧩 MCP Gateway Status"** panel: `HyperCode MCP Server: down`.

Three layered causes, all from the **Sep 8 image rebuild pulling a newer `mcp` SDK
(1.27.1)** — same *class* as the Sept 2026 HYPER-SILLs outage but subtler (no crash,
just rejects requests):

1. **421 Misdirected Request on every in-cluster call.** `mcp` SDK ≥1.9 ships
   `mcp/server/transport_security.py`; FastMCP defaults `transport_security` to
   `enable_dns_rebinding_protection=True` with
   `allowed_hosts=['127.0.0.1:*','localhost:*','[::1]:*']`. `localhost:8823` passes;
   bare `127.0.0.1` **and** `hypercode-mcp-server:8823` both 421. The dashboard's MCP
   proxy (`agents/dashboard/app/api/mcp/[...path]/route.ts`) fetches
   `http://hypercode-mcp-server:8823/sse` by **Docker service name** → 421. `route.ts`
   treats a 421 as a *successful* fetch (only catches thrown errors) → returns
   `{status:"down"}` on the first candidate, never tries the rest.
   **Fix:** `services/hypercode-mcp-server/server.py` now passes
   `FastMCP(..., transport_security=TransportSecuritySettings(allowed_hosts=[…, "hypercode-mcp-server:*", "0.0.0.0:*"], allowed_origins=[…]))`.
   SDK localhost defaults kept, so an IDE's `http://localhost:8823/sse` still works.
2. **Container `unhealthy`.** The compose healthcheck probed `/sse` — a long-lived
   MCP event stream — so `http.client.getresponse()` blocked past the timeout every
   cycle. `server.py` adds a non-streaming `@mcp.custom_route("/health")` (FastMCP
   1.27.1 has this decorator, no auth); `docker-compose.agents.yml` healthcheck now
   probes `/health`.
3. **Version drift.** `requirements.txt` said `mcp[cli]>=1.28.1,<2` but the running
   image had **1.27.1** — the `>=` line was never actually built. Pinned **exact
   `mcp[cli]==1.27.1`** (the version `server.py`'s API usage — `custom_route`,
   `TransportSecuritySettings` kwarg — is validated against). Bump deliberately +
   re-test, never `>=`.

- **Verified:** `/health` 200; `/sse` 200 by service name with **no `Invalid Host
  header` warnings** in the MCP server logs; dashboard `/api/mcp/health` →
  `{"status":"ok","transport":"sse"}`; container `healthy` (FailingStreak 0);
  `agent-registry` sees it healthy, no crash loop.

Files changed: `services/hypercode-mcp-server/server.py`,
`services/hypercode-mcp-server/requirements.txt`, `docker-compose.agents.yml`.

## ⚠️ Loose ends / deferred (on purpose)

1. **`mcp-gateway:8820` + `mcp-rest-adapter:8821` — still DOWN.** They are the MCP
   panel's *preferred* path (`route.ts` tries `mcp-rest-adapter:8821/health` first,
   falls back to the direct `:8823/sse` probe — which is what now works). Both are
   `--profile agents`, not built; `mcp-gateway` has an Exited(1) history
   (docker-levelup 2026-09-07 loose end). **Not worth 2 containers + a debug session
   for a status panel while RAM is tight.** If you want the full REST path later:
   `docker compose --profile agents up -d --build mcp-gateway mcp-rest-adapter`
   then debug the Exited(1).
2. **`hypercode-mcp-server` real root-fix for the healthcheck** is the new `/health`
   route (done). No further action — noted only so nobody re-adds a `/sse` probe.
3. **`HYPERCODE_MCP_SSE_URL` env** is candidate #1 in `route.ts`'s SSE list — that's
   the override lever if the service name ever needs to change.

## Stack state at handover

**FINAL state (2026-09-10 ~20:00Z): 41 containers up, obs stack UP.**

- **Observability stack (12): taken down mid-session, then RESTARTED at Lyndz's
  request (~20:00Z).** It was found UP at session start (restarted after the
  2026-09-09 handover left it down). During the MCP rebuild the 4 GB box was at
  **110 MB free / 1 GB swap** with obs + fleet both up — Docker Desktop was thrashing
  (21-min image build, `docker exec` overlayfs errors, `docker logs` empty, probe
  timeouts). Stopped all 12 by name (`docker stop`, **not** `compose down` —
  `--profile observability down` targets the whole project; all obs data is on named
  volumes so stop→start loses nothing but the downtime scrape gap) → freed ~1 GB,
  did the MCP rebuild, then **`docker start`ed all 12 back in two batches** (exporters
  first, then TSDBs), checking `hypercode-core` health between. **Core stayed
  `healthy`, 0 restarts** — no repeat of the 2026-09-09 Exited(137) cascade.
  - Now healthy: grafana (:3001, login `welshdog`), prometheus, prometheus-cloud,
    loki, tempo, alertmanager, cadvisor, node-exporter, promtail. pyroscope +
    grafana-agent have no healthcheck (show "running" — normal).
  - Stop/start commands if needed again:
    ```
    docker stop  grafana grafana-agent prometheus prometheus-cloud loki tempo pyroscope alertmanager promtail cadvisor node-exporter celery-exporter
    docker start grafana grafana-agent prometheus prometheus-cloud loki tempo pyroscope alertmanager promtail cadvisor node-exporter celery-exporter
    ```
  - ⚠️ The box runs obs + the *current* minimal fleet (~29 pre-obs) fine. It does
    **not** survive obs + the full agent fleet (`--profile agents`/`hyper`) — the
    2026-09-03 rule still holds. Stop idle agents before scaling the fleet with obs up.
- **`celery-exporter`: `unhealthy`** after the obs restart — **app is fine** (logs:
  `Started celery-exporter on port 9808`, actively reporting "Task queue depth"). The
  healthcheck probe times out at 10s under the tighter RAM with obs back. Cosmetic /
  probe-only; may self-settle. It's just a metrics exporter.
- **`hypercode-dashboard`: `unhealthy`** — pre-existing, since the mid-session
  memory-thrash window (NOT caused by the obs restart). Docker Desktop bug:
  `open /var/lib/docker/rootfs/overlayfs/661eff…: no such file` — the container's
  exec mount is broken so the healthcheck can't run. **The Node app serves fine**
  (verified `/api/mcp/health` + `/api/fleet` → 200 this session). Fix:
  `docker restart hypercode-dashboard` recreates the mount. Not done this session
  (left to Lyndz's call).
- `agent-registry` (:8077): **new this session**, built + up + healthy, 42 agents
  tracked. `restart: unless-stopped` — stays up across reboots now.
- `hypercode-mcp-server` (:8823): rebuilt (`mcp==1.27.1` pinned) + recreated, healthy,
  serving `/sse` by service name and `/health` for probes.
- `coder-studio` / `fcc-proxy` / `safety-shepherd`: untouched this session (see the
  2026-09-09 handover — free `/ide` path via fcc-proxy, and the API_KEY rotation list
  still stands).
- Orphan-container warning for `fcc-proxy` on `docker compose` commands is expected
  (it's from `docker-compose.fcc.yml`, not the root set) — **do not** `--remove-orphans`.

## ONE next task

Both status panels are green. Pick up the **2026-09-09 handover's** track:
**Increment 1c (ND persistence) + Increment 2** per the plan, or the picker-honesty
polish (flip `components/views/ModelPicker.tsx` so the free/FCC options are the
enabled default).

⚠️ Rotation list from 2026-09-09 still stands: `.env` `API_KEY` (`hc_d104ae9…`) and
the old `ANTHROPIC_AUTH_TOKEN` value are both burned via tool-output leaks — rotate +
recreate **dashboard + coder-studio + safety-shepherd** together on the next
full-fleet cycle.

🎉 Nice one BROski♾️ — fleet registry + MCP gateway panels both back to green.
