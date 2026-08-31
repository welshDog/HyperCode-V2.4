# 🏁 Session Handover — 2026-08-31 · "Dispatch-safety cards e/a/b shipped; CI outage root-caused to two commits + an account billing lock"

> Continues from `docs/NEXT_SESSION_HANDOVER_2026-08-24.md`.
> Full technical record (kept outside the repo, at `H:\HYPERFOCUSZONE\HperCore\`):
> `hypercode-session-full-report-2026-08-31.md` §9–§13.

---

## ⚡ TL;DR

1. **Four dispatch-boundary safety cards are on `origin/main`, all locally green, none CI-verified** (see blocker #4):
   | Commit | Card | What |
   |---|---|---|
   | `00adef59` | (d) | `agents/crew-orchestrator/dispatch_capability.py` — deny-first classifier (was already shipped last session) |
   | `669c31e9` | (e) v1 | agent-safety job added to `quality-gate.yml` — **superseded**, reverted in `d2842bcd` |
   | `d2842bcd` | (e) | **new `.github/workflows/agent-safety.yml`** — crew + fleet safety suites in their own CI lane, per-process |
   | `97ceed9a` | (a) | per-agent strict `check_dispatch()` in crew + fleet, `agents/shared/safety_contract.py`, crew mirror test |
   | `e64ca4b5` | (b) | `agents/crew-orchestrator/dispatch_capability.json` (all-`mutation`, 10 keys) + `.github/scripts/check_readonly_executor_capabilities.py` honesty check + `registry-honesty` job |

2. **The CI blackout is three stacked failures**, root-caused this session:
   - **Stage 1 — `60e1b351` (2026-04-28)**: `ci-python.yml` rewritten 150→33 lines, lost its `on: workflow_call` trigger. `quality-gate.yml`'s `uses: ./.github/workflows/ci-python.yml` orphaned. **`quality-gate.yml` has been mechanically invalid since April.**
   - **Stage 2 — `3a00f449` (2026-07-15, "ci: standardize workflow permissions")**: injected malformed `on:` / `permissions:` headers into ~23 workflow files. Commit message is inverted vs its effect. Also committed junk paths and mangled `.github/dependabot.yml`.
   - **Stage 3 — GitHub Actions account billing lock (active since ~2026-08-31 14:45Z)**: *every* Actions job across the `welshDog` account fails to start — "The job was not started because your account is locked due to a billing issue." Confirmed on `Agent Safety Suites`, `HyperCode Health Check`, `Security — CodeQL`.

3. **`a243f3dd` (Lyndz, 18:15) fixed 3 of the ~23 stage-2 headers** — `ci-js.yml`, `ci-python.yml`, `ci-security.yml`. It did **not** restore `ci-python.yml`'s `workflow_call`, and did **not** touch `quality-gate.yml` — so **`quality-gate.yml` is still dead** (its own malformed `on:` header + the still-missing `workflow_call` on its `ci-python.yml` callee). The safety suites deliberately do **not** depend on that chain — they run from `agent-safety.yml`, a standalone lane that can't inherit its failure.

4. **Docs synced this session**: this handover, `WHATS_DONE.md` (2026-08-31 entry), and the session-report §9–§13 at HperCore root. Memory file `safety-gate-boundary-work.md` (Claude's cross-session memory) updated too.

---

## 🔴 What's Actually Left

### Card (c) — wire the seam into the live dispatch path (~1–2h)

`agents/crew-orchestrator/main.py:524` `_safety_check_dispatch(agent_name, task_type, task_id, description)` currently calls **only** `safety_gate.evaluate_dispatch` (fail-open). Card (c) adds the strict path in parallel:

- `dispatch_capability.needs_strict_path(agent_name)` (card d) — decides which route
- for a `mutation` verdict, also call `safety_client.check_dispatch(DispatchRequest(...))` (card a)
- **Sharp edge — normalise `agent_name` to hyphenated ONCE at the boundary.** `settings.agents` (`config.py`) carries both underscore keys (`backend_specialist`) and hyphen keys (`coder-agent`); the registry and the Shepherd both speak hyphenated. `main.py:750` already does `.replace("-", "_")` for the *URL* lookup only. Do the hyphen-normalisation in `_safety_check_dispatch` and add a test pinning **both** key styles resolve to the same classification.
- **Do not flip enforcement yet.** `check_dispatch()`'s verdict is recorded/compared, not acted on. The mirror test (`agents/crew-orchestrator/tests/test_safety_client_mirrors_gate.py`, already green) proves the two paths send the Shepherd byte-identical requests, so their verdicts are comparable — that comparison is the canary.

### The flip — after card (c) AND a green canary

`agents/crew-orchestrator/safety_gate.py`:
- default `SAFETY_SHEPHERD_MODE` `monitor` → `enforce`
- invert the 3 `_fails_open` assertions in `tests/test_safety_gate.py` → `_blocks` — **for the mutation-capable route only**. The fail-open dispatch path for `read_only` executors stays fail-open by design.
- Gate the flip on a **Shepherd-health canary**: check `safety-shepherd` recent uptime / error rate first. A safe gate that is unavailable all day just trains the team to disable it under pressure.

### B session — repo-wide CI recovery (blocked on the billing lock)

1. **Prerequisite: clear the GitHub Actions billing lock.** Nothing below is verifiable until then.
2. **`quality-gate.yml`** — fix its own malformed `on:`/`permissions:` header AND restore `ci-python.yml`'s `on: workflow_call` + its 5 inputs (recover from `f2fb97e8`), or the `python-ci` job stays an invalid `uses:` reference.
3. **~20 other stage-2 malformed workflow headers** — `git show 3a00f449 --stat` → subtract later rebuilds (`a243f3dd` did 3) → fix each from `git show 3a00f449 -- <file>` (patterns differ per file) → `actionlint` pass. Note: `iac-scan.yml`'s workflow-lint job (the actionlint guard) is itself among the stage-2 casualties.
4. **Design calls (per-item, Lyndz)** — which `60e1b351` deletions were deliberate cost-cuts vs unnoticed casualties: SBOM + license-compliance jobs (`security-comprehensive.yml −344`), the 18-agent CRITICAL-CVE image matrix (`trivy-scan.yml −118`). Check whether Dependabot itself is dead (mangled `.github/dependabot.yml`, 25+ stale dependabot branches).
5. **5 pre-existing failures in `.github/scripts/tests/test_live_repo_integration.py`** (`0086a882`, 2026-08-24, unrelated to this session's work). The `registry-honesty` job deliberately runs only `test_check_readonly_executor_capabilities.py`, not the whole `.github/scripts/tests` dir, so these stay invisible. Fix or quarantine them, then widen the job's pytest scope.

### Verify the four cards once billing is back

`workflow_dispatch` `agent-safety.yml` → both matrix legs (`crew-orchestrator`, `fleet-controller`) plus `registry-honesty` should go green. Local baselines: crew suite **38**, fleet-controller **27**, honesty-check suite **15**, `check_readonly_executor_capabilities.py` real-repo run **PASS**.

---

## 🗝️ Key Facts

- **`agent-safety.yml` triggers** on `push`/`pull_request` to `main` touching `agents/{crew-orchestrator,fleet-controller,shared}/**`, `pyproject.toml`, `.github/scripts/**`, `docker-compose*.yml`, or the workflow itself; plus `workflow_dispatch`. The `docker-compose*.yml` path is load-bearing — without it, adding `docker.sock` to a `read_only` agent's compose service would not fire the honesty check.
- **`dispatch_capability.json` is keyed hyphenated** and every key must resolve to a real compose service (roster-drift guard in the honesty check — a phantom key fails the job). It currently has **zero `read_only` entries**: no agent has provably-clean container grants (`coder-agent`/`agent-x` carry `DOCKER_HOST`; the six specialists each hold a writable `./agents/NN-name:/app` workspace mount). The read-only route is armed and gated, not dormant — the first carve-out must pass the honesty check.
- **The honesty check never reads `DISPATCH_CAPABILITY_REGISTRY`** — that env var is dev/test-only for card (d)'s module; the CI check's `--registry` default is hardcoded to the real path.
- **`fleet-controller` is in no compose file** (added in `d6ec14b6`, silently removed in `e1afd436`). When it is re-composed, pin the "no `agents/shared` mount on fleet-controller" rule mechanically — extend `.github/scripts/check_fleet_controller_capabilities.py`.
- **crew mirror invariant**: `safety_client.check_dispatch` and `safety_gate.evaluate_dispatch` MUST keep sending identical Shepherd request bodies (agent / `category:"generic"` / tool / `target:None` / `domain:None` / `context{source, task_id, description[:200]}`). `test_safety_client_mirrors_gate.py` fails on any drift.

---

## 🧭 Method Rules (carried forward — hard-won)

- **Verify against the artifact** (clone, `git grep`, `git show`, directory listing, commit history) — never a search index. Index zeros are false negatives; proven repeatedly this arc.
- **A green test suite that certifies the wrong contract is worse than no tests.** `safety_gate.py`'s `_fails_open` tests were "tested to stay wrong." Every card this session is tested to stay *right* — fail-safe direction pinned.
- **Concede with evidence** — a SHA, a line number, a byte count — or don't concede.
- **Check `WHATS_DONE.md` before suggesting anything.**
- **Nothing wired that changes runtime behaviour before its proof lands.** Cards (d)/(a)/(b) are all deliberately unwired; card (c) is where the seam goes live, and only after the canary.
- Sacred repo rules apply (`docker-ce-cli` not `docker.io`, `from app.X import Y`, 4-space Python indent, `.env` never committed, Redis DB 1 cache / DB 2 rate limits).
