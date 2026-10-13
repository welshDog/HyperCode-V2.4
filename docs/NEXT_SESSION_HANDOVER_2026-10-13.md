# 📋 NEXT_SESSION_HANDOVER — 2026-10-13 (CI image scanning + runtime tests)

> Scope of this session: **CI / published images, then live rollouts.** `coder-agent` (CI image), `hypercode-dashboard` (UI fixes) and `healer-agent` (new restart policy) were rolled in the live stack
> (see the dated sections below); nothing else in the live stack was changed. `main` at the time of writing: `cbfacc7e` (+ this docs update).
> Older handover for the HyperCrew / live-stack side: `docs/NEXT_SESSION_HANDOVER_2026-10-03.md`.

## 🌅 START HERE (2 minutes, read-only)

1. `git fetch && git status -sb` in `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4` (tree was clean, on `main`).
2. `gh run list --workflow docker-push.yml --limit 3` → the latest push run should be green (last: run `38357688832`, 61 jobs, 30 of them `security-scan`).
3. If you are about to rebuild/restart anything locally: `python scripts/ram_guard.py --for build` first (8 GB host rule still applies).

## 🎉 THE SHORT VERSION

- **Every image `docker-push.yml` publishes (30) scans clean** for fixable HIGH/CRITICAL (Trivy). The per-push `security-scan` job now covers all 30 (advisory, exit 0). Docker Scout was removed (no Scout entitlement on the runner).
- **The workaround images are runtime-tested:** `scripts/ci/images-integration.sh` (35 checks, all pass) via `gh workflow run images-integration.yml`.
- **Found + fixed a long-standing bug** on the way: `docker-mcp` in `coder` crashed on launch (unpinned `mcp` resolved to 2.3.0). Pinned `mcp==1.28.1` in its venv (#580).

## What shipped (all merged to `main`)

| PR | What |
|---|---|
| #566 | `security-scan`: Docker Scout → Trivy (core + crew-orchestrator) |
| #568 | `hyper-architect` (~34 findings, 2 CRITICAL) → 0: multer/proxy-addr/path-to-regexp, npm removed from runtime, `apk upgrade`, + `architect-image-check.yml` |
| #569 | Python tooling pins (jaraco/wheel), otel/protobuf, fastapi/starlette, mcp-server 1.28.1, devops compose+kubectl dropped, spawner builds Compose from source on Go 1.26.9, coder pipx shared pip removed, + `agent-images-check.yml` |
| #570 | `security-scan` widened to all 30 images |
| #571, #576 | memstream / mcp-server / skillweaver run non-root; memstream + skillweaver added to the PR image check (+ their own CVE fixes) |
| #580 | coder: pin `mcp==1.28.1` inside the `docker-mcp` venv |
| #579 | `images-integration.yml` + `scripts/ci/images-integration.sh` |
| closed | #567 (one-off scan workflow, superseded) |

## 🚀 Local rollout (done 2026-10-13 ~08:35 BST)

- **Only `coder-agent`** was rolled (`devops-engineer` is not part of the local stack). No local build (RAM guard AMBER): pulled the CI image `ghcr.io/welshdog/hypercode-v2.4/hypercode-coder:latest` (`5a4e9b7a8049`, includes the #580 `docker-mcp` fix), kept the old one as **`hypercode-v24-coder-agent:pre-rollout-20261013`** (`82839e91d008`, rollback), retagged the new one `hypercode-v24-coder-agent:latest`, then `CREW_LLM_BASE_URL=http://fcc-proxy:8083 docker compose <4-file set> --profile agents up -d --no-deps --no-build coder-agent`.
- **Verified:** healthy, 0 restarts, proxy var kept, `docker_mcp` imports, agent port 8002. Memory dipped to ~1139 MB during the swap (stop rule 1200) and recovered.
- **Crew test through it (5 runs, real model via fcc-proxy):** 3 ALLOW / 2 BLOCK = 60 %, same as the earlier 9/15; both BLOCKs were verifier FAILs on model output (no timeouts, no 5xx). n=5 cannot show a regression. The ALLOWs settled XP/coins to the owner; handover gate always rejected (no PR).
- **End-of-session checks (09:00-09:10 BST):** `images-integration.yml` 35/35 on main; latest push run green; stack: 35 running, 0 paused, all 9 key services healthy with 0 restarts; core `/health` 200. Only unhealthy container: **`hypercode-dashboard`** (its health probe fails with a Docker-level `open /var/lib/docker/rootfs/overlayfs/...: no such file or directory`, restarts=0; not diagnosed or touched).
- `results/latest-*.md|json` show as modified in the working tree: they are `qa-engineer`'s latest-run report, rewritten by the crew test (left uncommitted).

## ⚠️ What this does NOT mean

- Beyond `coder-agent`, `hypercode-dashboard` and `healer-agent`, **the live local stack still runs the images it had before**; the other fixed images exist on GHCR (`:latest`) and in PR checks only. Rebuild/recreate deliberately (RAM guard first; recreating `coder-agent`/`qa-engineer` drops `CREW_LLM_BASE_URL` unless it is in the shell env).
- Scans ignore unfixed CVEs and anything below HIGH. Moderate `npm audit` items remain (e.g. `uuid` in `agents/architect`).
- The integration test checks startup + basic requests only (no core, Postgres or LLM): it is not proof of real agent work. It is manual, not a gate.

## Workarounds to revisit when upstream ships fixes

- Docker's `docker-compose-plugin` 5.6.0 is on Go 1.26.8 → `services/agent-spawner` builds Compose v5.6.0 itself (Go 1.26.9, x/net 0.60.0). Drop this when Docker ships a rebuilt plugin.
- `kubectl` latest (v1.37.1) is on Go 1.26.8 → removed from `devops-engineer` (nothing referenced it). Re-add only if needed.
- pipx's shared pip (26.2.1) vendors old msgpack/urllib3/setuptools → deleted from the `coder` image after install.
- `memstream` is still on EOL `python:3.9-slim` (clean today after `apt-get upgrade`); move to 3.11+ when Flask 2.3.3 is checked.
- New image added to a `push-*` job? **Add it to the `security-scan` matrix list by hand.**

## Open items (none started)

1. Normal (non-superuser) users get 0 RAG results (ingest stamps the superuser id) — design decision needed.
2. `POST /memory/reset` returns a misleading 503 while Chroma runs `ALLOW_RESET=FALSE`.
3. ~23 workflows have invalid YAML and fail instantly (see memory `hypercode-healthcheck-yaml-never-valid`).
4. `hypercode-dashboard` flaps unhealthy; `crew-orchestrator` has no fully pinned lockfile; CodeRabbit never posts a review (rate limited).
5. The `remember` plugin SessionStart hook is slow (~30 s average).

## ✅ Healer restart policy fixed + rolled out (2026-10-13 ~13:32 BST)

- **Problem (from the healer's own logs, since 2026-10-10 22:29Z):** 34 `docker_restart`s (Backend 20, Mission Control 11, Ollama 3), **0 recoveries**, 29 "still unhealthy after heal"; failed-heal counters stuck at 32 / 18. Causes in `agents/healer/mape_k_engine.py`: one non-healthy probe with Z>3 (e.g. one 5 s timeout under VM load) restarted a service; a restart was judged after ONE probe 5 s later while core boots in ~90-230 s (so every restart was recorded as failed); the counters only reset on a successful heal, which could never happen (backoff stuck at the 30 min cap); the DEGRADED branch was dead code; the dashboard got docker-restarted (its 12 Oct 13:30Z restart under build load left it with a missing rootfs, unhealthy ~19 h).
- **Fix: PR #586 (`7b4843f0`):** restart needs **3 consecutive** bad probes (`HEALER_RESTART_MIN_CONSECUTIVE`); post-restart verification polls for the service's `startup_grace_seconds` (core 240, dashboard 90, ollama 60) in a **background task** (so one slow boot never blocks probing the rest); failed-heal counters/backoff **reset after 6 healthy probes** (`HEALER_RESET_AFTER_HEALTHY`); per-service `probe_timeout` (core/dashboard 10 s); **Mission Control (dashboard) is alert-only**. 17 tests in `agents/healer/tests/test_mape_k_policy.py`, run in CI by the new `healer-policy-tests.yml` (`agents/healer` is not in the repo pytest `testpaths`). Old-vs-new replay: one slow 5xx probe, one timeout, two timeouts in a row: restart True -> False; 3 DEGRADED at low latency False -> True; a service booting a few probes late judged OK False -> True.
- **Rolled out:** image `42a9267d5770` built locally (rollback tag `hypercode-v24-healer-agent:pre-policy-fix-20261013`, `1382b0520d26`), `healer-agent` recreated 13:32 BST with `--force-recreate --no-deps --no-build healer-agent` once the VM was calm. The build needed `fcc-proxy` stopped by name (restarted after); lowest WSL available during it ~1333 MB (build context is the whole `agents/` tree, ~160 MB, slow).
- **Observed after ~75 min (to 14:47 BST):** 0 `docker_restart`s; 219 `alert_only` notices (Grafana / HyperHealth API / Prometheus, the obs services Lyndz keeps stopped, ~1/min each = noise, not action); `hypercode-core` and `hypercode-dashboard` untouched since before the rollout (up since 11:42Z and 12:09Z); stack 35 running, 0 unhealthy. **Not yet proven:** how it handles a real slow boot or a real load spike (no such event happened). Check with `docker logs -t healer-agent 2>&1 | grep -E "docker_restart|recovered|Backing off"`.
- **Also seen:** core (11:42Z) and the dashboard (12:09Z) were restarted during today's builds, very likely by the OLD healer (the 12:09Z one lines up with the healer image build); unproven because the old healer's logs went with its container. Both healthy, `exec` fine on all 35 containers.
- **Not done:** a host-load-aware guard (skip restarts while several services degrade at once); concurrent probing (probes are sequential, so a 10 s timeout can delay a cycle); silencing the repeated `alert_only` spam for deliberately stopped services.

## ✅ Dashboard UI bugs fixed + image rebuilt (2026-10-13 ~11:37 BST)

- **Found by a headless-browser tour** of http://127.0.0.1:8088/ (repo-local Playwright; the Chrome extension was not connected): 15 API endpoints all 200, 0 console errors; two real bugs. **#584 merged** (`37817299`): (1) `components/views/MetricsView.tsx:25` had `⏳` as JSX *text*, so users saw the literal characters while Metrics loaded (now the real emoji; regression test `__tests__/MetricsView.loading.test.tsx` fails on the old line); (2) the shell was a fixed `240px 1fr` grid, so at 390px the content was ~150px wide: under 760px it now stacks (wrapping top bar, scrolling nav strip, panes in one column). Dashboard vitest 264/264.
- **Rebuilt + recreated:** image `9f13f123ffc1` (rollback tag `hypercode-v24-dashboard:pre-mobile-fix-20261013`). Verified live: loading text correct with `/api/metrics` held back; at 390px main = 390px wide, panes 370px, no overflow/clipping on `/`, `/health`, `/ide`, `/control`; 768/1500px unchanged; 0 errors.
- **RAM warning (breached the 1200 MB stop rule):** guard was AMBER (WSL avail ~1335 MB; GREEN needs 1500). With Lyndz's OK, `fcc-proxy` was stopped for the build (restarted after, healthy), which only reached 1444 MB; the Next.js compile then dipped to **976 MB** (nothing was killed). A local dashboard build is at the edge of this machine; prefer a CI-built image if this recurs. Recreate the container only after the VM is calm (load < 5, cpu pressure < 30 %).
- **Not fixed (observations):** the top bar is ~200 px tall on phones (all controls wrap; a collapsible menu would be a separate change); `/api/mcp/health` takes ~3.6 s (MCP page looks stuck "Loading" for a few seconds); the Docker Zone page is static text labelled "Live status" with stale content (e.g. the Scout baseline); Mission Control shows 10 red "Down" agents that are simply not deployed locally, and the dashboard shows "System Health: CRITICAL" for the same reason. Mission Control also shows `hypercode-dashboard` with 36 auto-heals, which supports the healer-restart concern below.
- Browser-tour scripts/screenshots were scratch files (not committed); a repeatable tour would live under `agents/dashboard/e2e` if wanted.

## ✅ Dashboard fixed (2026-10-13 ~10:07 BST)

- **Cause:** `hypercode-dashboard` was "unhealthy" for ~19 h with the app fine (HTTP 200 on :8088). `docker exec` into it failed with `open /var/lib/docker/rootfs/overlayfs/<id>: no such file or directory` (missing container rootfs mount in the Docker VM), so its `docker exec`-based health probe could never run (failing streak 2253). It began right after the healer's `docker_restart` of it at 12 Oct 13:30:58Z (Z-score anomaly) under heavy build load; the healer had restarted it 4 times since 11 Oct evening. Only this one container of 35 was affected. The exact mechanism is not proven (Docker's events for that window were not retained).
- **Fix:** waited for the VM to calm (load ~4.5, CPU pressure <10%, WSL avail >1200 MB), then `docker compose <4-file set> --profile agents up -d --no-deps --no-build --force-recreate dashboard` (service name is `dashboard`, container `hypercode-dashboard`). Healthy, 0 restarts, `/`, `/ide`, `/api/health` 200. Rollback tag `hypercode-v24-dashboard:pre-recreate-20261013`. **A plain restart would not have fixed it; recreate.**
- Two never-started leftovers removed (`wonderful_poitras` postgres + its empty anonymous volume, `20d5073ea64c_skillweaver`); the real `skillweaver` untouched. The dashboard's "System Health: CRITICAL" banner is expected (stopped obs stack, celery-worker, agents outside the local stack).

## ▶️ NEXT TASK (one sentence)

Let the new healer run through a real load spike or restart (watch `docker logs -t healer-agent | grep -E "docker_restart|recovered|Backing off"`), and meanwhile add a CI-built dashboard image (it is not in `docker-push.yml`, and its local Next.js build dipped RAM to 976 MB) so the next UI change doesn't need a risky local build.

## Gotchas learned (also in memory `hypercode-ci-image-scanning-trivy-2026-10-13`)

- A path-less "Python" Trivy target with `AnalyzedBy: sbom` = a vendored `bom.cdx.json`, not an installed package.
- `workflow_dispatch` only works for workflows already on `main`; to run a PR-branch workflow use `gh run rerun <run-id>`.
- Python heredocs collapse `\`-newline continuations (write scripts with the Write tool); read `docker-push.yml` as UTF-8.
- Wait for pending PR checks before merging (I merged #571 with three still pending; they passed).
