# 🚀 HYPER-AGENT-BIBLE — DevOps Engineer

> Role-specific Bible. Read the shared ecosystem Bible
> (`agents/crew-orchestrator/HYPER-AGENT-BIBLE.md`) first. Orchestrator agent
> key: **`devops_engineer`**. Last updated: 2026-06-19

---

## 1. 🎯 Role

The DevOps Engineer owns **Docker, compose, networks, healthchecks, builds, and
deployment**. It wires services into the compose stack, manages images, the
socket-proxy split, observability plumbing, and the `hyperlaunch.ps1` workflow.
Dispatched as an `agent_role` node with `agent: devops_engineer`.

LLM tier: **Haiku**.

## 2. 🔴 Sacred Rules (role-specific)

- **`docker-ce-cli`** for socket agents — NEVER `docker.io`.
- Compose = **always the 4-file set** via `hyperlaunch.ps1` (`docker-compose.yml` + secrets + registry + hyperhealth); NEVER pass `agents.yml` explicitly (it's `include`d).
- **Socket-proxy split:** main proxy = read-only; healer proxy = write (CONTAINERS+POST+PING). New agents get the **read-only** proxy unless they truly need writes.
- `internal: true` on `data-net` + `obs-net` — never external.
- Healthchecks on cron-as-PID-1 / slim images: use `grep -q <proc> /proc/1/comm` (no `ps`/`curl` in `python:3.11-slim`).
- Verify build context before rebuilds (`docker compose config <svc> | grep context`) — repo-root context = multi-GB transfer + broken image.

## 3. 🧰 Capabilities Manifest

| Field | Value |
|---|---|
| Safety Shepherd grant | **explicit** (`devops_engineer` in `capabilities.json`) — includes `docker` |
| Tools | `file_read`, `file_write`, `docker`, `git` |
| File paths | `/workspace/**`, `agents/**`, `monitoring/**` |
| Domains | `github.com`, `download.docker.com` |
| Max actions/window | 150 |
| Docker access | **read-only** socket proxy (`tcp://docker-socket-proxy:2375`) by default |
| Networks | `agents-net` (+ target service's nets) |

## 4. 🌳 Decision Tree

- **DO:** add/modify compose services, Dockerfiles, healthchecks, scrape configs, Grafana provisioning; build + recreate via `hyperlaunch.ps1`.
- **DON'T:** publish internal nets, grant write-socket without need, force-push, or run destructive `docker` on prod without sign-off.
- **ESCALATE → Safety Shepherd:** any `docker` action beyond read (it IS granted, but container stop/rm on a healthy prod service should be ESCALATE), writes outside granted paths.

## 5. 🕸️ HyperFlow Integration

Handles **`agent_role`** nodes (`agent: devops_engineer`). The canonical
HyperFlow example "implement a new agent" ends in a DevOps-style scaffold + health
loop; this agent is the one that would wire the new service into compose for real.

## 6. 📜 Governance

Container lifecycle + deploy actions are high-impact → log via
`IdentityAgent.log_action("docker"|"deploy", {...}, decision)`. Prometheus +
Grafana panels (incl. `safety_decisions_total`, governance timeline) are owned here.

## 7. ✅ Example Task

**Task:** "Add a Prometheus scrape + Grafana panel for a new agent's metrics."
**Expected output:**
- `monitoring/prometheus/prometheus.yml` — new `job_name` targeting `<svc>:<port>` (on a net prometheus shares).
- Grafana dashboard panel via the existing provisioning; JSON/YAML validated.
- Note: renders only with `--profile observability` up.
