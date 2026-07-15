# 🛡️ Safety Shepherd (P0-2)

Runtime policy brain that sits between the orchestrator and tool calls. Every
"dangerous" proposed action (docker, external HTTP, file writes, Stripe, Discord)
can be routed through Safety Shepherd, which returns **ALLOW · BLOCK · ESCALATE**
based on a per-agent capabilities manifest.

- **Port:** `8096` (bound `127.0.0.1` on host)
- **Networks:** `agents-net` + `data-net` (never `app-net`)
- **Docker:** read-only socket only (it does not write)
- **Stripe:** exempt — never gated (sacred rule)

## Decision flow

```
exempt(stripe) → ALLOW
hard-blocked target (.env/secrets) → BLOCK
unknown agent → ESCALATE
blocked domain → BLOCK
file_write outside allowed paths → BLOCK
action-rate ceiling hit → ESCALATE
tool not granted → ESCALATE
external HTTP to non-allowlisted domain → ESCALATE
dangerous category without grant → ESCALATE
otherwise → ALLOW
```

`ESCALATE` raises a human approval request on the shared `approval_requests`
Redis channel (the Mission Control dashboard already streams it) and also via
core `GET/POST /api/v1/dashboard/approval-requests`.

## Capabilities manifest

`capabilities.json` — per-agent `tools`, `file_paths` (globs, `**` supported),
`domains`, `max_actions`. Hot-reloaded on file change (no restart). Edit grants
there; the decision engine (`policy.py`) needs no code change.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | liveness |
| POST | `/evaluate` | `X-Agent-Key` | decide on a proposed action |
| GET | `/capabilities` | no | current manifest |
| GET | `/safety/events` | no | recent decisions (Grafana / dashboard) |
| GET | `/metrics` | no | Prometheus (`safety_decisions_total`) |

### Example

```bash
curl -s -X POST localhost:8096/evaluate \
  -H "X-Agent-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d '{"agent":"coder_agent","category":"file_write","tool":"file_write","target":"backend/app/x.py"}'
# -> {"decision":"ALLOW","reason":"action within granted capabilities", ...}
```

## Observability

- Every decision logs as JSON to stdout → **Loki** (obs-net).
- `safety_decisions_total{decision,category,agent}` → Prometheus → Grafana.
- `GET /safety/events` backs a Grafana / Mission Control panel.

## Run

```powershell
.\hyperlaunch.ps1 --profile safety up -d safety-shepherd
curl http://localhost:8096/health
```
