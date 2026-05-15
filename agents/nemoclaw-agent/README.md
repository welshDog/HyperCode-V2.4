# 🤖 nemoclaw-agent

Autonomous code-health sidecar for HyperCode V2.4.

Scans the repo with **ruff + detect-secrets + AST checks**, computes a normalised
0–100 score, maps it to a grade (S/A/B/C/D), and persists each scan to Postgres
so the agent can compute deltas, hotspots, and reward improvements over time.

This is **Layer 1** of the "NemoClaw Alive" arch — the heartbeat. Layers 2–6
(memory, voice, action, inter-agent, thinking) stack on top of this foundation.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET`  | `/health`  | none | Liveness + dependency status |
| `POST` | `/scan`    | `X-API-Key` | Run a scan; returns score + grade + top issues |
| `GET`  | `/history` | `X-API-Key` | Last N scans from Postgres |

### POST /scan

Optional body:
```json
{ "targets": ["backend", "agents"] }
```

Defaults to `NEMOCLAW_SCAN_TARGETS` env (comma-separated).

Response:
```json
{
  "scan_id": "uuid",
  "persisted": true,
  "score": 87,
  "grade": "A",
  "grade_label": "CLEAN",
  "grade_emoji": "✅",
  "total_files": 423,
  "counts": { "critical": 0, "high": 2, "medium": 11, "low": 5 },
  "top_issues": [ { "file": "...", "line": 42, "severity": "high", ... } ],
  "scanned_at": "2026-05-15T...Z",
  "scan_targets": ["backend", "agents"]
}
```

**Secret leakage guard:** `detect-secrets` findings only surface the file + line
+ secret *type* — the actual matched value is never returned.

## Grade table

| Range | Grade | Label | Emoji |
|---|---|---|---|
| 95–100 | S | LEGENDARY | 🏆 |
| 80–94  | A | CLEAN | ✅ |
| 65–79  | B | GOOD | 👍 |
| 50–64  | C | NEEDS WORK | ⚠️ |
| 0–49   | D | SOS MODE | 🆘 |

Score deductions: critical −10, high −3, medium −1, low −0.3 (clamped 0–100).

## Auth

Every request except `/health` requires `X-API-Key` (or `X-Agent-Key`) matching
the `HYPERCODE_API_KEY` env. In production this is mounted via Docker secret at
`/run/secrets/api_key`.

## Running locally (outside Docker)

```bash
cd agents/nemoclaw-agent
pip install -r requirements.txt
HYPERCODE_API_KEY=dev WORKSPACE_PATH=../../ uvicorn main:app --port 8099
```

Then in another shell:
```bash
curl http://localhost:8099/health
curl -X POST http://localhost:8099/scan -H "X-API-Key: dev" -H "Content-Type: application/json" -d '{"targets":["agents/nemoclaw-agent"]}'
```

## Integration points

- **broski-bot** calls `/scan` via `cogs/health_check.py` for the `/health`
  slash command (grade embed).
- **healer-agent** (future): correlate restart loops with regressions in
  affected files.
- **morning-briefing agent** (future): include daily grade trend in posts.
- **focus session** (future): baseline scan on `/focus start`, post-scan on
  `/focus stop` → reward BROski$ for measurable improvements.

## Files

```
analyzer.py    — scanner core (ruff, detect-secrets, AST)
db.py          — async Postgres adapter (lazy; silent no-op if unavailable)
main.py        — FastAPI app (/scan, /history, /health) + auth middleware
Dockerfile     — python:3.11-slim, non-root, healthcheck on :8099
requirements.txt
.env.example
```
