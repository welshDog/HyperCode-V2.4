# 📋 NEXT_SESSION_HANDOVER — 2026-10-13 (CI image scanning + runtime tests)

> Scope of this session: **CI / published images only.** The live local stack was **not** touched or health-checked this session
> (the last live-stack work was the slim `hypercode-core` swap on 2026-10-11/12, see `WHATS_DONE.md`). `main` at the time of writing: `b71634e6`.
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

## ⚠️ What this does NOT mean

- **The live local stack is still running the images it had before**; nothing was rolled out. The fixed images exist on GHCR (`:latest`) and in PR checks, not in your running containers. Rebuild/recreate deliberately (RAM guard first; recreating `coder-agent`/`qa-engineer` drops `CREW_LLM_BASE_URL` unless it is in the shell env).
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

## ▶️ NEXT TASK (one sentence)

Roll the fixed images into the local stack: rebuild and recreate `coder-agent` and `devops-engineer` (RAM guard GREEN first), then run `gh workflow run images-integration.yml` and a quick `/health` sweep to confirm.

## Gotchas learned (also in memory `hypercode-ci-image-scanning-trivy-2026-10-13`)

- A path-less "Python" Trivy target with `AnalyzedBy: sbom` = a vendored `bom.cdx.json`, not an installed package.
- `workflow_dispatch` only works for workflows already on `main`; to run a PR-branch workflow use `gh run rerun <run-id>`.
- Python heredocs collapse `\`-newline continuations (write scripts with the Write tool); read `docker-push.yml` as UTF-8.
- Wait for pending PR checks before merging (I merged #571 with three still pending; they passed).
