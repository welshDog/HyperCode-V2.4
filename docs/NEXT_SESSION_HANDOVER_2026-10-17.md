# 📋 NEXT_SESSION_HANDOVER — 2026-10-17 (backups, secret files, one shared key, JWT rotated)

> Current as of **2026-10-17 ~12:30 BST**, checked live. `main` = `7b421d50`. Full per-change detail: `WHATS_DONE.md` (top entry) and `git log`.
> Machine clock is BST (UTC+1). All PR numbers below are merged unless marked.

---

## 🌅 START HERE (5 minutes, read-only)

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`.
2. **BROskiPets checkout:** `H:\HYPERFOCUSZONE\BROskiPets-LLM-dNFT` must stay on branch `feat/relay-api-key-file` until its **PR #3** merges. `evolve-relay` builds from that folder; building it from `main` drops file-key support and the relay then rejects every caller.
3. `python scripts\ram_guard.py` (was GREEN, WSL available ~1.5 GB). `docker ps --filter health=unhealthy -q | wc -l` should be `0`.
4. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\probe_inter_agent_key.ps1` should end `no rejections`.
5. **Log in to the dashboard again.** The JWT rotation killed every stored browser login. Until you do, the Health page shows "Docker feed unavailable, HTTP 401". That is the browser calling core without a token, not a fault.

## 🎉 THE SHORT VERSION

- **Backups are live:** Postgres, Redis/MinIO/Chroma, daily, copied to `C:` and encrypted into Google Drive. Restore drills passed. A watchdog (13:00 and 18:00) alerts on failures, disk, Redis memory and policy, and 401/403s to core.
- **Redis** evicts with `volatile-lru` from the compose file (survives a restart).
- **Secrets are files, not env values.** One shared inter-agent key now sits in `secrets/inter_agent_key.txt` for 9 agents. The public default `dev-master-key` no longer opens the healer or any key-enforcing peer.
- **JWT signing secret rotated** (2026-10-17 11:30) and the dashboard token re-minted (expires **2026-11-16**).
- **63 lost BROski$ awards recovered** (+660 XP, wallet 7340 at the time); a watchdog check now catches any new gap.
- **Dashboard** polling/scroll fixes merged; the dashboard is healthy and every page returns 200.

## What shipped (all merged)

| What | PR |
|---|---|
| Core degraded (JWT/MinIO) fixed, Chroma persistence, Redis `volatile-lru`, tested backups + off-site copy + alerts | #599 |
| hyperhealth reads `API_KEY_FILE`; stack config committed (FCC/throttle includes, core tuning) | #601, #600 |
| Economy consumer reads the master key from its secret file; stale-key 401/403 alert | #602 |
| `read_secret()` vendored into 22 agent files so `*_FILE` works; safer key minting | #603 |
| WSL/Docker Desktop restart runbook + staged start script; lessons from the first real run | #604, #605, #607 |
| XP reconcile watchdog + backfill tools | #606 |
| celery health probe hard-killed after 20 s (hung probes had piled up to 1 GB) | #608 |
| Shared-key probe; shared key rollout (overlay + `rollout_inter_agent_key.ps1`); healer inbound auth; throttle-agent sends the key; healer/throttle/evolve-relay rebuilt | #609, #612 (carried #610/#611, closed) |
| Dashboard shared polling, Pulse retry, scrollable main area | #598 |
| `rotate_jwt_secret.py` understands the secret-file layout | #613 |
| **Open, other repo:** `evolve-relay` reads `HYPERCODE_API_KEY_FILE` | BROskiPets-LLM-dNFT **#3** (its CI also fails on `main`: missing `supabase` module) |

## 🟢 LIVE STATE (checked 12:30 BST)

- 37 containers, **0 unhealthy**. Fleet (dashboard `/api/fleet`): 12 healthy, 5 running, 10 down, 15 not deployed, 42 total. Error rate 0%, DLQ 0, Safety Shepherd 50/50 ALLOW.
- Down because of the 8 GB ceiling (not faults): `backend-specialist`, `broski-pets-bridge`, `database-architect`, `devops-engineer`, `frontend-specialist`, `goal-keeper`, `hyperhealth-api`, `mcp-gateway`, `mcp-rest-adapter`, `nemoclaw-agent`. Most useful to bring back: `hyperhealth-api`, `broski-pets-bridge`, `nemoclaw-agent`.
- Observability stack is off (Grafana frame empty, `celery-exporter` DOWN): expected.
- `fcc-proxy` is running again. `throttle-agent` is in OBSERVE mode (decision unchanged).

## 🔑 How the secrets work now (read before touching any agent)

| Secret | Where | Who reads it |
|---|---|---|
| Shared inter-agent key | `secrets/inter_agent_key.txt` | crew-orchestrator, coder-agent, qa-engineer, safety-shepherd, coder-studio, evolve-relay, governor, healer-agent, throttle-agent (all as a file) |
| Core JWT signing secret | `secrets/jwt_secret.txt` (`JWT_SECRET_FILE`) | hypercode-core only |
| Dashboard service token | `secrets/dashboard_service_jwt.txt` | dashboard (cached in memory: recreate it after a change) |
| Master API key | `secrets/api_key.txt` | core, economy consumer |
| Per-agent keys | `secrets/agent_api_key_<agent>.txt` | each agent |

- **Roll the shared key:** `scripts\rollout_inter_agent_key.ps1` (dry run by default, `-Apply` to change, `-PassKeyAsEnv` only as a rollback). `throttle-agent` is not in it: `docker compose -f docker-compose.yml up -d --no-deps --force-recreate throttle-agent`.
- **Rotate the JWT secret:** `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight), then `--yes`. Since #613 it handles the file layout. Its first full run with the file layout is still ahead (the 2026-10-17 rotation was done by hand with the same steps).
- **Starting any "down" agent:** use the secrets overlay (`hyperlaunch.ps1`, or the file set from the container's compose labels). A plain `compose up` gives it `dev-master-key`, which the peers now reject.
- **Local-only files to clean up when you are happy** (gitignored, they hold retired secrets): `secrets/jwt_secret.txt.bak-jwt-rotation-20261017-112927`, `secrets/dashboard_service_jwt.txt.bak-jwt-rotation-*`, `secrets/inter_agent_key.old.txt`.

## 🪤 Traps that cost time this round

- **Windows PowerShell 5.1:** a function with a 1-2 letter name collides with an alias (`R`→`r`, `H`→`h` = Get-History) and **echoes its argument into the error text. That printed two secrets into a session on 2026-10-17.** Never name helpers that way; hash with an inline expression; pass secrets by file or stdin.
- `--format '{{index .Config.Labels "x"}}'` returns nothing in PS 5.1 (embedded double quotes). Use `{{json .Config.Labels}}`.
- Health checks that spawn a process (`celery inspect ping`) can hang under load and pile up (Docker does not kill a timed-out probe). Cap them with `timeout -s KILL`.
- `agent-registry` restarts containers it sees die, about 13 s later. `docker stop` of optional containers can be undone by it.
- Build routine: stop `fcc-proxy` (optional) → `ram_guard.py --for build --wait 150` → **one** build at a time, in the background. The guard flips AMBER right after each build; wait for GREEN again.
- Squash-merging stacked PRs leaves the next one conflicting. Merge the top branch (after merging `main` into it) and close the rest as superseded.
- **Check what a "no rebuild needed" agent really reads** before assuming: `qa-engineer` and `coder-studio` already had file-aware key code under different function names.

## ⏭️ OPEN ITEMS

1. **BROskiPets PR #3** — decide (merge anyway, or fix the CI `supabase` import first).
2. Bring back `hyperhealth-api` and `broski-pets-bridge` (one at a time, RAM check between).
3. Optional: Health page uses a server-side proxy with the service token so it works without a login.
4. Re-mint the dashboard token before **2026-11-16** (this will be the first end-to-end run of the new rotate script).
5. Delete the retired-secret backups listed above.
6. Still not deployed: V2.4 Railway, HYPER-SILLs v1.4, Stripe live (see memory index).

## 🎯 THE ONE NEXT TASK

Decide on BROskiPets PR #3, then start `hyperhealth-api`.

---
> Stack facts are in `docs/STATUS.md`; this file is the story. Short sentences first, detail after.
