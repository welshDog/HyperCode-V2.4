# 📋 NEXT_SESSION_HANDOVER — 2026-10-18 (CI recovery, leaked-secret finding)

> Current as of **2026-10-18 ~12:30 BST**. `main` = `a66b26f8`. Per-change detail: `WHATS_DONE.md` (top entry) and `git log`.
> Machine clock is BST (UTC+1). All PR numbers below are merged unless marked. The previous handover (`NEXT_SESSION_HANDOVER_2026-10-17.md`) still applies for the host, backups and secrets.

---

## 🌅 START HERE

1. `cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`, `git fetch`, `git status -sb`.
2. **Rotate the three leaked secrets first (Lyndz's action, see below).** Nothing else in this file is as urgent.
3. Host checks from the 2026-10-17 handover still apply (RAM guard GREEN before any build, BROskiPets checkout stays on `feat/relay-api-key-file` until its PR #3 merges).

## 🔴 THE FINDING: live secrets in the PUBLIC repo's git history

`welshDog/HyperCode-V2.4` is public. The Gitleaks job (Security — Comprehensive Scan) reports 64 findings across 1,525 commits. Each flagged line was re-read from history and compared with the local `.env` / `secrets/` values (names only; **no value was printed or saved**).

| Secret | Leaked in (still in `main`) | Local source |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | `HEALTH_CHECK_REPORT.md` | `secrets/orchestrator_api_key.txt` |
| `MEMSTREAM_API_TOKEN` | `memory/memstream-integration-report.md` | `secrets/MEMSTREAM_API_TOKEN.txt` |
| Stripe webhook secret (TEST mode) | `RUNBOOK_BLOCKERS.md` | `secrets/stripe_webhook_secret.txt` |

Already retired or harmless: the old `API_KEY` (now `inter_agent_key.old.txt`), the `ANTHROPIC_AUTH_TOKEN` in `.claude/settings.local.json` (rotated), `DISCORD_USER_ID` (an ID). The other ~50 hits look like example curl headers, doc samples and redaction-test fixtures, but were not hand-checked one by one.

**Order:** (1) rotate the three, (2) redact those lines in the three HEAD files (PR), (3) add `.gitleaks.toml` allowlisting fixtures/examples only. **Never allowlist before rotating**, that would hide live leaks. Rotation restarts services: use the existing rotate scripts and the RAM-guard rules. Trap: `gitleaks-action` redacts the SARIF snippet ("REDACTED"); re-read lines with `git show <sha>:<file>`.

## 🎉 WHAT CHANGED TODAY (all merged)

| PR | What |
|---|---|
| #620 | Regression Guard installs backend deps; really runs now |
| #623 | Docker build/GHCR/Trivy permissions, Hyper Agents CI (ruff 0.17, black, mypy, coverage floor 55) |
| #624 | Quality gate valid again (`workflow_call` for python, `inputs.*` read directly, floors 55, e2e off, audit = critical only) |
| #625 | Dashboard lockfile `npm audit fix` (18 -> 8 findings) |
| #626 | Dashboard e2e works 5/5 (production build in CI, default stubs, `hyper-shell` test id) |
| #627 | Regression Guard split: blocking vs advisory `regression-known-red`; Gate 2 heavy jobs manual-only |
| #628 | pip-audit: 7 IDs with no fix ignored, review by **2026-11-18** |

Dependabot #621/#622 were closed with an explanation.

## ⏭️ WHAT IS STILL RED OR OPEN

- **Security Gate:** red only because of Gitleaks (above). pip-audit, Trivy, Semgrep pass.
- **Advisory job `regression-known-red`:** 21 failures, by design visible: the live-stack files (`test_api_agents`, `test_agent_observability`, `test_swarm_load`, `test_coder_capabilities`) that need the running Docker stack. The 20 stale unit tests were repaired in PR #631 and are blocking now (Regression Guard 336 passed). Fix a file, then move it into the blocking list in `.github/workflows/hyper-agents-gate2-e2e.yml`.
- **No Legacy Paths Guard:** live `HyperCode-V2.0` references (docker-bake.hcl, mcp configs, helm Chart.yaml, `agents/healer/cli.py`, k8s scripts).
- **Gate e2e off** (`run_e2e: false`): `tests/e2e/playwright.config.ts` still uses `next dev`; apply the production-build approach from #626, expect real axe findings.
- **Gate 2:** `tests/hyper_agents/e2e` does not exist; the Full Stack compose test fails on `networks.agents-net conflicts with imported resource` and needs secrets. Manual-dispatch only until fixed.
- **Also:** 7 "autonomous AI synthesis engine" files landed in `main` inside #623 (decide keep/remove); ~25 old Dependabot PRs (#506-#575); PR #616 (system test docs); an untracked `docs/reports/HYPERCODE_FULL_HEALTH_TEST_REPORT_2026-10-17.md`.

## 🪤 TRAPS LEARNED (cost real time)

- A reusable workflow's `github.event_name` is the **caller's** event, never `workflow_call`; read `inputs.*` directly.
- `scripts/validate_workflow_yaml.py` only checks duplicate keys; it does not prove GitHub accepts the file.
- CI installs the **latest** ruff; reproduce lint in a fresh venv, not with the local version.
- Many files here are **CRLF**: use the Edit tool or CRLF-aware code, or an edit silently doesn't apply.
- `gh run download` / `git show` are safer than guessing at CI logs; failure artifacts (`error-context.md`) pinpointed the hydration bug.
- Next dev pages did not hydrate in CI (HMR websocket); a production standalone build fixed it.
- A skipped `needs:` job also skips its dependents unless they use `if: always()`.

## ONE NEXT TASK

Rotate the orchestrator key, the memstream token and the Stripe webhook secret, then tell the assistant so it can open the redaction PR.
