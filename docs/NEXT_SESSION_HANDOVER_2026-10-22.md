# 📋 NEXT_SESSION_HANDOVER — 2026-10-22 (upgrade report executed: Brain fix live, core right-sized)

> Current as of **2026-10-22 ~10:35 BST**. Machine clock is BST (UTC+1). Earlier handovers (`-10-17`, `-10-18`, `-10-20`) still apply for the host, backups, secret-file layout and the security gate. **No secret values appear in this file.**

---

## 🌅 START HERE

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`. The checkout was fast-forwarded to `origin/main` on 2026-10-22 and still holds old uncommitted work (CI, tests, reports, a deleted `docs/archive/HEALTH_CHECK_REPORT.md`, an untracked 2026-10-17 report, `DEV_REPORT.md`). Do not bulk-commit or discard it.
2. Check RAM before any build: `python scripts/ram_guard.py --for build`. It read **AMBER** at the end of this session (the four-agent builds still went through, but do not stack more).
3. **Carried over, untouched this session:** the Railway CLI login (`railway login` is interactive, the user must run it). The `COURSE_SYNC_SECRET` rotation is **done locally** (see the section below); only the remote side is unverified.

## 🔑 COURSE_SYNC_SECRET rotation (applied locally 2026-10-22 ~11:15 BST)

- **Applied to three local files:** the HyperCode `.env`, `secrets/COURSE_SYNC_SECRET.txt`, and `Hyper-Vibe-Coding-Course/.env` (the course app's own copy, which held the same old value as core's `.env`). Before the change the `.env` and the secrets file held *different* old values, as the 2026-10-20 handover warned: core reads the `.env` value (`${COURSE_SYNC_SECRET}` in `docker-compose.core.yml` and `docker-compose.agents.yml`).
- **Recreated one at a time** with the four stack compose files (`docker-compose.yml`, `.secrets`, `.registry`, `.hyperhealth`): `broski-pets-bridge`, then `hypercode-core`. Verified: both Docker-healthy, core `/health` 200, secret set in core's environment, 0 containers unhealthy, 0 auth errors in either log over 10 minutes.
- **Backups:** `secrets/rotation-backup-20261022/` (`.env`, `COURSE_SYNC_SECRET.txt`, `course.env`), gitignored. Delete them and `secrets/COURSE_SYNC_SECRET.txt.new` after a few quiet days.
- **NOT confirmed (remote side):** the user saved the new value in the course Supabase project, but that project is **stopped for lack of funds** and the Supabase MCP returned "no permission" on `get_project`, so it was not verified that the save took effect. When the project is restored, check the edge function's secret matches the local value; a mismatch shows up as sync **401s**. If the live course site on Vercel keeps its own copy, update it there too: no hosted setting was touched.

## ✅ What was done (from `UPGRADE_REPORT_FOR_DEVS_2026-10-21.md`)

| Item | Result |
|---|---|
| Brain `4a7b142` constellation fix | Pushed to `origin/main` (fast-forward; 127 tests passed first). `graph.json` stayed unstaged. |
| Brain images | Rebuilt one at a time (`COMPOSE_PARALLEL_LIMIT=1`) and recreated: `agent-hyper-brain-core`, `agent-mcp-bridge`, `agent-focus-tracker`, `agent-morning-briefing`, **and `hyper-brain`**. No agents needed stopping. |
| Live check | `:8100`, `:3301`-`:3304` `/health` all 200; `/constellation/map` 200 with graph data (was 500). |
| HyperCode compose resources | `6da44b22` (redis, celery-worker, memstream limits/reservations right-sized) and `bb71b232` (memstream CPU limit 2.0 → 0.25). Only `docker-compose.core.yml` was committed. |
| memstream live | Recreated; `NanoCpus=250000000`, 512 MiB, healthy, runs as `appuser`. Redis PONG, AOF on, RDB ok; core `/health` 200. |
| HYPER-SILLs `bef442c` | Windows-safe validation scripts and test isolation. 24 tests, smoke test, registry sync and index checks all pass. |

## ⚠️ Report corrections (the report is wrong or incomplete here)

- **`hyper-brain` is missing from the report's rebuild list.** Port `:8100` is served by the `hyper-brain` service (`docker-compose.brain.yml`, `Dockerfile.hyper-brain`), which bakes in `hyper_brain_core.py`. Rebuilding only the four `agent-*` services does **not** make the `/constellation/map` fix live. Rebuild/recreate `hyper-brain` too (profile `brain-agents`, `up -d --no-deps hyper-brain`).
- **memstream CPU:** the report said the cap was already 0.25; the committed file still had `2.0` (only the reservation had dropped). Fixed in `bb71b232`.
- Section 3.3's `git rebase origin/main` advice does not work with a dirty tree that overlaps upstream. What worked: apply the one-file change in a throwaway `git worktree` from `origin/main`, push from there, then fast-forward the main checkout.

## 🪤 Traps hit this session

- A shell whose cwd is inside a worktree blocks `git worktree remove` ("Permission denied" on Windows). Leave the folder first, then delete it.
- `docker compose config` in a fresh worktree fails for a missing `.env`; validate the YAML another way (`yaml.safe_load`).
- Recreating a service from a **stale local compose file silently reverts its limits**. Always sync the checkout to `origin/main` first.
- `git push` takes ~1-2 min because of the pre-push eval hook; run it in the background.

## 🧹 Loose ends (decisions for the user)

- A stash entry `claude-sync-memstream-report-20261022` is left in this repo (the auto-mode classifier blocked dropping it). It holds the user's original edit to `memory/memstream-integration-report.md`. Drop it with `git stash drop` once happy. Copies of the original and the conflicted file are in the session scratchpad.
- `memory/memstream-integration-report.md` has one **uncommitted** edit: the weak `broski123` health token replaced by `${MEMSTREAM_HEALTH_TOKEN:-dev}`. Upstream already redacted the API token there.
- Brain repo: `HYPERFOCUS_ZONE/06-AI-Context/graph.json` is modified by the graph-refresh process. Never include it in a code commit.
- A wildcard `awk` allow rule was removed from `HperCore/.claude/settings.local.json` (it matched far more than intended).

## ↩️ Rollback

- Brain constellation fix: `git revert 4a7b142` (Brain repo), then rebuild `hyper-brain`.
- Compose resources: `git revert bb71b232 6da44b22`, then `up -d --no-deps redis celery-worker memstream` from the reverted file.
- HYPER-SILLs: `git revert bef442c`.
- Old Brain images were not tagged for rollback; the previous `hyper-brain` image id was `266a84bfd044`, only reachable if it was not pruned.

## 🧱 DHI pilot — source prepared, image verification blocked by RAM

A single-service Docker Hardened Images pilot now targets the actual deployed HyperHealth build context, `agents/hyperhealth` (not the unused `services/hyperhealth` duplicate):

- `agents/hyperhealth/Dockerfile` uses a Python 3.11.18 Debian 12 DHI dev builder and runtime image, runs nonroot as UID/GID 65532, and retains the multi-stage venv build.
- `agents/hyperhealth/entrypoint.py` replaces the shell-based startup wrapper: API mode runs `alembic upgrade head` before Uvicorn, and Compose's worker command is exec'd unchanged.
- `agents/hyperhealth/.dockerignore` keeps local env/secrets, caches, and tests out of the build context.
- The API healthcheck uses Python's stdlib `urllib` because the DHI runtime does not include curl/shell; the merged HyperHealth Compose healthcheck was updated the same way.
- Compose services now use `read_only: true`, `tmpfs` `/tmp` (64 MiB, noexec/nosuid), `cap_drop: [ALL]`, and `no-new-privileges:true`; code inspection found no required persistent file writes in the service containers.
- Added `.github/scripts/check_dhi_contract.py` plus a CI workflow `.github/workflows/hyperhealth-dhi-contract.yml`. The gate checks both API/worker definitions use the real `agents/hyperhealth` build context, paired versioned DHI bases, nonroot runtime, shell-free entrypoint behavior, Python healthcheck, build-context secret exclusions, and Compose runtime hardening. It executes the real entrypoint in subprocess probes while mocking only Alembic/process replacement: API mode must migrate before Uvicorn; worker mode must preserve Compose's command without running migrations. Run: `python .github/scripts/check_dhi_contract.py --check`. The CI workflow runs this source gate and tests only; it does not build images.
- Added tests proving API mode runs Alembic before replacing itself with Uvicorn, worker mode skips migrations and preserves the Compose command, and deliberate contract mutations fail. Verification completed: **12 DHI gate/entrypoint tests and 39 HyperHealth tests pass**, entrypoint/API/worker compile, four-file Compose config validates, both existing HyperHealth containers remain healthy, and their current endpoints are HTTP 200.
- **Update 2026-10-27 — built and deployed:** After stopping only the optional `fcc-proxy` (used by `coder-agent`/`qa-engineer`) and confirming RAM guard GREEN, built `hyperhealth-api` and `hyperhealth-worker` separately with `COMPOSE_PARALLEL_LIMIT=1`. Isolated smoke checks confirmed UID 65532 plus API/worker imports under read-only root, tmpfs `/tmp`, dropped capabilities, and no-new-privileges. Recreated API and worker individually with `--no-deps`. Live: both healthy, zero restarts, worker Redis heartbeat present, API `:8095/health` 200, core `:8000/health` 200. Guard was GREEN after rollout at 1608 MiB WSL available.
- Restored `fcc-proxy` with the documented two-file compose and `--no-deps --no-build`; proxy health 200 and Docker healthy. `qa-engineer` can reach it. `coder-agent` was already exited before the temporary proxy stop and was left untouched.
- Follow-up guard reads are AMBER again (WSL available ~1.4 GiB), so no additional builds/recreates until GREEN.

When the guard is GREEN, from the HyperCode root run one service image build at a time with the four canonical compose files:

```powershell
$env:COMPOSE_PARALLEL_LIMIT='1'
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.registry.yml -f docker-compose.hyperhealth.yml build hyperhealth-api
```

Before deploying, inspect `agents/hyperhealth/entrypoint.py` for both modes, verify `docker image inspect` reports user `65532:65532`, then recreate `hyperhealth-api` and `hyperhealth-worker` one at a time using the same four-file set and `--no-deps`. Verify `http://127.0.0.1:8095/health`, worker Redis heartbeat, core `/health`, and logs. If the image fails, keep the currently running containers and report the failure; do not use `--remove-orphans`.

## 👉 ONE next task

When the RAM guard is GREEN, run `python .github/scripts/check_dhi_contract.py --check`, build only `hyperhealth-api`, and smoke-test the image as UID 65532 before rebuilding/recreating production services; separately, when the Course Supabase project is restored, verify its edge-function secret matches local `COURSE_SYNC_SECRET` and update any Vercel copy.
