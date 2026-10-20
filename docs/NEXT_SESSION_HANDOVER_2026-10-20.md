# 📋 NEXT_SESSION_HANDOVER — 2026-10-20 (secrets rotated, security gate green, hyperhealth upgraded)

> Current as of **2026-10-20 ~08:30 BST**. Machine clock is BST (UTC+1). The previous handovers (`NEXT_SESSION_HANDOVER_2026-10-17.md`, `-10-18.md`) still apply for the host, backups and the secret-file layout. **No secret values appear in this file.**

---

## 🌅 START HERE

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`. The local checkout is behind `origin/main` and holds old uncommitted changes (a deleted `docs/archive/HEALTH_CHECK_REPORT.md`, a modified `memory/memstream-integration-report.md`, an untracked 2026-10-17 report): do not discard them blindly.
2. The leaked-secret item from the 2026-10-18 handover is **closed** (see below). Nothing is urgent.
3. Check free RAM before any build or recreate (`Get-CimInstance Win32_OperatingSystem`): on 2026-10-19 a Docker Desktop restart left the host at ~0.02-0.25 GB free for hours, which made health checks slow and flapped `celery-worker`. Close the IDE and other heavy apps first.

## 🔐 Secrets: what really happened and what is done

The 2026-10-18 note said three live secrets were in public history. A full-history comparison of every value in the live `.env` and `secrets/*` (done in memory, names only) found:

- **Really exposed and in use**: `ORCHESTRATOR_API_KEY`, `MEMSTREAM_API_TOKEN`, and the `.env` `HYPERCODE_API_KEY` (an old master key in an October audit report).
- **Not in use**: the leaked sync/Stripe values in `RUNBOOK_BLOCKERS.md` history were stale `secrets/COURSE_SYNC_SECRET.txt`, `SHOP_SYNC_SECRET.txt` and `stripe_webhook_secret.txt` files that no container reads (the stack uses different `.env` values for those, which were never leaked). The files were replaced with fresh values. If the leaked 60-character `whsec_` was a real Stripe endpoint secret, roll it in the Stripe dashboard.
- **Nothing is published to the internet** (no tunnel container; `tailscaled` is private), so the practical risk was low.

**Rotated 2026-10-19 (done):** new values in `.env` + `secrets/orchestrator_api_key.txt` + `secrets/MEMSTREAM_API_TOKEN.txt`; then `memstream`, `broski-bot`, `crew-orchestrator`, `dashboard`, `hypercode-core`, `hyperhealth-worker` were recreated one at a time. Verified: the new orchestrator key is accepted and the old one gets 401; zero auth failures in the logs; stack back to 32 healthy + 6 without health checks. Rollback copies of every changed file are in `secrets/rotation-backup-20261019/` (gitignored; delete after a few quiet days).

**Where the old values also lived (all updated):** `agents/broski-bot/.env` (the bot reads its OWN `.env`, not the main one), and the `.env` files of `3d Print Genie/service`, `HyperFocus-The-Anime-Build`, `Hyper-Vibe-Coding-Course` and `HperCore/.env`. The `postgres` container still has the old (now dead) values in its environment via `env_file`; it never reads them and they clear at its next recreate. The five old `.env.bak*` files were deleted.

## 🛡️ Security gate

| PR | What |
|---|---|
| #685 | Redacted the live values from three report files still in `main`. |
| #686 | `.gitleaksignore`: the 64 reviewed historical findings by exact fingerprint (no pattern, file or rule ignored). Every one was re-read: rotated, retired or not a secret. |
| #687 | `aiohttp` 3.14.3 → 3.14.4 and `yarl` 1.20.1 → 1.25.1 in `backend/` (3 aiohttp CVEs; aiohttp 3.14.4 needs yarl ≥ 1.25.1, which is why the audit first failed to run at all). |
| #688 | Minimum safe bumps for patch/minor pins in 8 more requirements files. |
| #692, #693 | hyperhealth plan, then Tasks 1-3 (below). |

"Security — Comprehensive Scan" on `main` is **all green** (Semgrep, pip-audit, Trivy, Gitleaks, Security Gate). On push events gitleaks only scans new commits; the weekly Monday run scans everything and is clean because of #686. To prove a gate before merging, dispatch the workflow on the branch: `gh workflow run security-comprehensive.yml --ref <branch>` (job logs only download after the WHOLE run finishes).

## 🩺 hyperhealth upgrade (deployed 2026-10-20 ~00:15 BST)

- Requirements: `fastapi==0.149.0`, explicit `starlette==1.9.0`; the unused `pyOpenSSL` and `slowapi` were removed. Image advisories 20 → 0; the image is smaller (339 MB vs 361 MB).
- New: `agents/hyperhealth/tests/test_api_smoke.py` (19 HTTP cases, passes on the old AND new pins) and the CI job `.github/workflows/hyperhealth-tests.yml` (none of these tests ran in CI before; run them from the repo root with `PYTHONPATH=.`).
- Deployed by tagging the tested image as `hypercode-v20-hyperhealth-api:latest` / `-worker:latest` (NOT built through compose, because the live checkout is behind `main`). Both services verified against the real Postgres: identical behaviour, zero restarts, worker checks at the baseline rate.
- **Rollback:** `docker tag rollback/hyperhealth-api:20261019 hypercode-v20-hyperhealth-api:latest` (same for the worker), then `.\hyperlaunch.ps1 --profile health up -d --no-deps --force-recreate hyperhealth-api` / `hyperhealth-worker`. Delete the rollback tags after a few quiet days.

## 🪤 Traps learned

- Recreate with `.\hyperlaunch.ps1` (4-file compose set) and mind **service names vs container names**: the dashboard's service is `dashboard` (container `hypercode-dashboard`). `no such service` while the old container stays healthy looks like success: check the container's `StartedAt`.
- A plain `docker compose` recreate falls back to the `dev-master-key` default (see the 2026-10-17 handover); never run unfiltered `docker compose config` (it prints `.env` secrets).
- Several consumers read their own env files: grep `agents/*/.env` and sibling project `.env` files (names only) before calling a rotation finished.
- Docs PRs need an entry in `docs/CHANGELOG_DOCS.md` (the docs-check fails otherwise; the file is CRLF).
- `pip-audit --no-deps` on pinned lines only sees DIRECT pins; resolve the file (`py -3.11 -m pip install --dry-run -r ...`) or audit the built image to see transitive CVEs such as `starlette` and `cryptography`.

## 📌 Open

1. **Other services still on old FastAPI/Starlette ranges** (each needs the hyperhealth treatment: tests first, then a rebuild): `agents/mission-executor` (fastapi 0.109.1 keeps `starlette<0.36`), `memstream` (flask 2 → 3), the root tooling list (`starlette` 0.52 → 1.x). Not urgent; most are not in the running stack.
2. Unaudited/unused requirements files: `backend/requirements-UPGRADED.txt`, `requirements-ai.txt`, `requirements-agents.txt`, `hyperstudio-platform/` (92, 94, 4 and 44 advisories respectively; not shipped).
3. `agents/coder-studio`: `claude-agent-sdk` 0.2.115 → 0.2.121 (could not be resolved on the audit machine; verify in CI or a build before shipping).
4. Delete `secrets/rotation-backup-20261019` and the older JWT / inter-agent key backups, and the two `rollback/hyperhealth-*:20261019` image tags, after a few quiet days.
5. Rebuild the other running images (`hypercode-core` etc.) when convenient so they pick up the aiohttp/yarl bump from #687.
