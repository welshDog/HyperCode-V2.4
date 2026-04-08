# HyperCode v2.4.0 — Release Notes
**Released:** 2026-03-29
**Branch:** `feature/hyper-agents-core`
**Tag:** `v2.4.0`

---

## What's New

### MCP IDE Integration
Any AI IDE that supports the Model Context Protocol can now talk to HyperCode natively.

**New service: `hypercode-mcp-server`** (port 8823, SSE transport)

10 tools exposed:
- `hypercode_system_health` — confirm the stack is alive
- `hypercode_list_agents` — all running agents with XP, level, coin balance
- `hypercode_agent_system_health` — deep CPU/memory/Redis metrics
- `hypercode_list_tasks` / `hypercode_create_task` — task management
- `hypercode_generate_plan` — run the full planning pipeline on any document
- `hypercode_get_logs` — live system log stream
- `hypercode_broski_wallet` / `hypercode_broski_leaderboard` — BROski$ economy
- `hypercode_execute_agent` — send commands to the crew orchestrator

**Claude Code** auto-discovers tools via `.mcp.json` in the project root — no manual config needed. See `docs/MCP_IDE_INTEGRATION.md` for Cursor and Windsurf setup.

---

### WebSocket Live Streaming
Mission Control Dashboard now receives agent events in real time.

- **Orchestrator `/ws/events`** — WebSocket endpoint that subscribes to Redis pub/sub (`ws_tasks`, `broski_events`, `approval_requests`) and fans out to all connected dashboards
- Seeds last 20 log entries on connect — no empty panel on first load
- `useEventStream` hook fully rewritten to WebSocket (the previous SSE proxy was broken)
- `useLogs` hook upgraded: WebSocket primary, HTTP poll fallback when disconnected
- `LogsView` shows `⚡ Live` (green) or `⏱ Polling` (amber) connection status

---

### Observability — 8/8 Prometheus Targets UP

Previously 7/9 with 2 phantom DOWN targets. Fixed:
- `PROMETHEUS_METRICS_DISABLED` was `true` in `docker-compose.yml` — flipped to `false`, `/metrics` endpoint now live on `hypercode-core`
- `throttle-agent` Prometheus scrape target commented out — it's profile-gated (`--profile agents`) so was permanently DOWN

Full audit documented in `docs/DOCKER_HEALTH_REPORT_v2.4.md`.

---

### Bug Fixes

| Component | Bug | Fix |
|-----------|-----|-----|
| `healer-agent` | Crash-loop: `ImportError` on relative import in `mape_k_api.py` | Changed `from .mape_k_engine` → `from mape_k_engine` |
| `healer-agent` | `IndentationError` in `mape_k_engine.py:26` (3-space vs 4-space) | Fixed indentation |
| `hypercode-core` | `/metrics` returns 404 | `PROMETHEUS_METRICS_DISABLED=false` |

---

## Stack Status

```
Tests:        58/58  ████████████ 100%
Docker:       19/19  ████████████ 100%
Prometheus:    8/8   ████████████ 100%
MCP tools:    10     ████████████ live on :8823
WebSocket:    live   ████████████ ws://localhost:8081/ws/events
```

---

## Quick Start

```bash
# Start the full stack including MCP server
docker compose up -d

# Verify MCP server is live
curl http://localhost:8823/sse

# Connect WebSocket stream
python -c "
import asyncio, websockets
async def t():
    async with websockets.connect('ws://localhost:8081/ws/events') as ws:
        print('Connected')
asyncio.run(t())
"

# Open Mission Control
open http://localhost:8088
```

---

## Upgrade Notes

If upgrading from v2.3.x:
1. `docker compose pull` to get new images
2. `docker compose build hypercode-mcp-server` to build the new MCP service
3. `docker compose up -d` — `PROMETHEUS_METRICS_DISABLED` is now `false`, metrics will appear in Grafana

---

*Built by @welshDog — HyperFocus Zone, Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*
*Co-authored with Claude Sonnet 4.6*
