# NEXT_SESSION_HANDOVER — HyperCode-V2.4 — 2026-09-03

> The session's mission lived in the **Brain repo**
> (`BROski-Obsidian-Brain-for-HyperFocus-z0ne/NEXT_SESSION_HANDOVER_2026-09-03.md`) —
> bake the constellation feature into `agent-mcp-bridge`. This file is the
> V2.4-side state. Full technical detail: `WHATS_DONE.md`'s 2026-09-03 entry.

## What changed in V2.4 (all on `main`, pushed)

| commit | one-liner |
|---|---|
| `994f3b24` | Prometheus (obs) moved to its own volume `prometheus-obs-data` — stops the TSDB-lock crash-loop vs `prometheus-cloud` |
| `5c51d1a6` | `prometheus-cloud` healthcheck probes `:9090` (internal) not `:9091` (host publish) |
| `97f2cd6c` | `security_opt: !override` on all 6 `docker-compose.observability.yml` blocks — works around compose v5.5's list-concat merge bug that blocked `--profile observability` |
| `11578cc3` | Grafana Postgres datasource: `${VAR:-default}` → plain `${VAR}` (Grafana provisioning doesn't do bash defaults) |

Plus a Grafana admin repair (`.env` `GF_SECURITY_ADMIN_USER` `lyndzwills` → `welshdog`
to match `grafana.db`; `.env` is gitignored so not committed).

## Box state right now

- **Full `--profile observability` stack is UP** (loki/tempo/pyroscope/promtail/
  node-exporter/cadvisor/alertmanager/celery-exporter + prometheus/grafana/minio/
  chroma). All healthy, 0 OOM. 38 containers running.
- **~31 idle specialist agents are STOPPED** to fit it on the 8 GB box. Restore
  list: `…/scratchpad/obs-stack-restore-list.txt`.
  **🔴 Don't `docker start` them while obs is up** — OOM. Tear obs down first
  (`docker compose … --profile observability down`, or `docker stop loki tempo
  pyroscope`), THEN restore agents.
- **Grafana `:3001`** — login **`welshdog`** (not `lyndzwills`), pw =
  `.env` `GF_SECURITY_ADMIN_PASSWORD`. 5/5 datasources OK, 11 dashboards.
- Prometheus obs `:9090` — 12/14 targets UP (`broski-bot`, `crew-orchestrator`
  down = pre-existing scrape-config mismatches).
- `agent-mcp-bridge` on baked image `sha256:0e8693ac…` (constellation feature).

## Next tasks in V2.4

None open from this session. Standing backlog is still `docs/NEXT_TASKS.md`
(item #2b MemStream, etc. — untouched).

## Gotchas surfaced this session

- docker compose **v5.5 concatenates single-item list fields** on same-service
  merge → use `!override`. Single-file recreate avoids the 5-file merge entirely.
- Grafana provisioning: **no `${VAR:-default}`**, plain `${VAR}` / `$__env{VAR}`.
- Grafana admin login must equal `.env` `GF_SECURITY_ADMIN_USER` or every login
  401s `[identity.not-found]`. It's `welshdog` here.
- `docker exec … /app/…` in Git Bash needs `MSYS_NO_PATHCONV=1`.
