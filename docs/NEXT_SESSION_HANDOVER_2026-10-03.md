# 📋 NEXT_SESSION_HANDOVER — 2026-10-03 (HyperCrew on Docker + host-RAM safety + security follow-ups)

> Current as of **2026-10-03 ~16:05 UTC**, verified live. Branch `claude/focused-darwin-ljrs8k` · draft PR #547. `WHATS_DONE.md` has the full detail and the exact PASS lines; live status beats this file.
> Rewritten as one clean document: every dated "UPDATE"/"RESOLVED" patch it had accumulated is folded in (history is in `WHATS_DONE.md` and `git log`).
> ⏱️ **Time labels:** this machine runs BST (UTC+1). Labels written before ~14:15 UTC in the older docs mix docker/UTC and local clock times; labels from 14:05 UTC on were checked against commit times and container timestamps. **Git commit times (`%z`) and `docker inspect` are authoritative; true UTC = local − 1 h.**

---

## 🎉 THE SHORT VERSION

- **HyperCrew runs on Docker and the happy path is proven:** guard **ALLOW** → Quest Settler (20 XP, 10 coins, "First Squad Run") → Scribe draft → handover gate (skipped on purpose, no PR). Run `b01b22bc-…`, with a real core restart in the middle.
- **Real model:** `fcc-proxy` → NVIDIA NIM `nemotron-3-ultra-550b-a55b` for builder and verifier. **Opt-in** (`CREW_LLM_BASE_URL`); it **sends crew text to NVIDIA**.
- **Host-RAM safety:** `scripts/ram_guard.py` → Task Scheduler job keeps the signal fresh → **throttle-agent in OBSERVE mode with a debounce** (pauses nothing).
- **Done since the 14:15 UTC handover (all deployed + live-verified):**
  1. IDE health check + 4 fixes — stale run cancelled, **Pulse panel shows real XP** (`63f5edd2`), 9 stray containers removed, Shepherd crew grants (`f83c8321`).
  2. **Shepherd applies real grants to hyphenated agent names** (`55aea70a`): `backend-/frontend-specialist`, `devops-engineer` (docker!), `database-architect`; `coder_studio` guarded by `exact_name_only`. 124 shepherd tests.
  3. **JWT signing secret ROTATED 15:13 UTC** (`scripts/rotate_jwt_secret.py`, you ran it): the exposed 10-year admin token now returns 403; new 30-day dashboard token **expires ~2026-11-02**.
  4. **Verifier tightened** (`d78fa0e3`, 15:29 UTC): a PASS must say `none` for problems and list none (else downgraded to FAIL); oversize (>8000) / no-op / `.env`-or-`secrets/` diffs are rule FAILs. 51 tests.

## 🟢 LIVE STATE (verified 16:01 UTC)

| Thing | State |
|---|---|
| Containers | **36 running, 0 paused, 0 unhealthy**; core, dashboard, orchestrator, coder-agent, qa-engineer, safety-shepherd, fcc-proxy, throttle-agent, healer all `healthy`, RestartCount 0 |
| `hypercode-core` | healthy. Restarted **14:19:55Z by `healer-agent`** (`docker_restart`, z-score 7.1, during the host memory squeeze — graceful exit 0, no OOM) and recreated **15:13Z** by the JWT rotation (new signing secret) |
| `hypercode-dashboard` | healthy; restarted ~15:13Z to load the re-minted token. ⚠️ An older **unexplained clean restart at 12:50:23Z** is still unexplained |
| `safety-shepherd` | healthy; recreated 14:18Z with the name-normalisation code. **Core + orchestrator still run `SAFETY_SHEPHERD_MODE=monitor`** (record, don't block) |
| `qa-engineer` | healthy; restarted ~15:35Z with the tightened verifier. `coder-agent` + `qa-engineer` run **with the proxy ON** |
| `throttle-agent` | healthy, `THROTTLE_MODE=observe`, 0 paused. Timeline since 12:48Z: **60 decisions** = GREEN 25, AMBER-pending (absorbed by the debounce) 21, AMBER 11, RED 3; **6 "would pause" lines, all in the two early episodes (12:50–12:51, 13:31)**; nothing since 15:05Z except one absorbed blip |
| Host signal writer | Task Scheduler `\HyperCode\HyperCode RAM Guard Signal` running; signal file ~16 s old, GREEN |
| Observability stack | **STOPPED** (12 containers; Grafana panel "refused to connect" is expected) |
| Memory (guard, 16:01Z) | **GREEN** — host free 803 MB, compression 1,597 MB, WSL available 1,627 MB |
| Git | branch in sync with `origin`; `results/*` shows modified from another process (not mine; never commit it) |

## ▶️ NEXT TASK (one sentence)

**Audit the older leak (open item 6): check whether `f1edc13e`'s `.claude/settings.local.json` "gateway token" in pushed history was ever a real credential, and rotate it if so.** Done today: throttle-agent stays in OBSERVE (Lyndz), `evolve-relay` compose path fixed, relay env trimmed.

## ⚠️ OPEN — NEEDS A DECISION FROM YOU (nothing here is started)

1. ✅ **throttle-agent: DECIDED 2026-10-03 (Lyndz) — stay in OBSERVE, no `enforce`.** Reasoning from the review: containers total only ~1.4 GB (tiers 4-6 ~563 MiB), `pause` frees no RAM, `stop` frees <~305 MiB and the healer fights it, and tier 6 holds `fcc-proxy` (the crew's model path). Your call: keep observe (recommended) + optionally take `fcc-proxy` out of tier 6 / add threshold logging. Still not done: a logon/reboot test of the scheduled task.
2. **Core + orchestrator `monitor` → `enforce`** — never without checking the Safety Feed for ESCALATEs first, and remembering the four agents' real grants now apply (e.g. `devops-engineer` may use docker).
3. ✅ **`evolve-relay` compose path FIXED 2026-10-03 (16:15 UTC):** the Pets repo lives at `H:/HYPERFOCUSZONE/BROskiPets-LLM-dNFT` (one level above HperCore), not next to HyperCode-V2.4. `docker-compose.bropets.yml` now uses `${BROSKIPETS_DIR:-../../BROskiPets-LLM-dNFT}` for both build contexts and the relay's `env_file` (now `required: false`); the combined project validates again (56 services). **Least-privilege trim DONE (16:44 UTC, `49f0cc6b`):** the relay now gets only 7 variables from the Pets `.env` via the gitignored `secrets/evolve_relay.env` (made by `scripts/make_relay_env.py`; 38 others are no longer passed), the container was recreated on the SAME image (no rebuild), healthy, restarts 0. Re-run the script after rotating any of those keys, then recreate the relay.
4. **Observability stack:** restart it or leave it off (needs ~1+ GB; the 4 GB WSL cap is tight).
5. **Dashboard token expiry ~2026-11-02:** re-run `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight, then `--yes`) before then. Also remove the `/permissions` rule you added for the old mint command if it is still there.
6. **Earlier leak in history:** `f1edc13e` says `.claude/settings.local.json` "contained a gateway token"; untracking does not remove it from pushed history. Rotate it if it was ever real.
7. **Verifier false FAILs:** the model is not deterministic, so a clean diff can occasionally FAIL (costs a re-run, never a bad PASS). Watch it; loosen only with evidence.
8. Original D1–D12 decisions, kill-switch compose wiring, a real GitHub token for the Scribe (do NOT configure one without asking): all still open and untouched.
9. The **unexplained dashboard restart** at 12:50:23Z — worth a look if it recurs. Also: `postgres` still holds a copy of the OLD (dead) JWT secret via `env_file:` until its next recreate (harmless).

## ❌ NOT PROVEN

Real GitHub PR publish · dashboard-side approval UI · "Paused (n)" with a *running* run · kill-switch compose wiring · the Task Scheduler job across a logon/reboot · `THROTTLE_MODE=enforce` (never run) · whether the observe would-pauses were right (review pending) · a full end-to-end crew run with the **tightened verifier** (probed live on synthetic diffs only) · `hyper-mission-api` / `ai-backend` with the new JWT secret (not running).

## 🔭 HOW TO REVIEW THROTTLE-AGENT OBSERVE MODE (read-only; a session-only check was scheduled for 17:07 local, job `d5a747ee`)

1. `python scripts/ram_guard.py --for check` — memory now.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status` — writer `Running`, signal age well under 120 s.
3. `docker inspect -f '{{.State.Health.Status}} r={{.RestartCount}}' throttle-agent` and `docker ps --filter status=paused -q | wc -l` (**must be 0**).
4. `docker logs throttle-agent 2>&1 | grep observe_decision` — the whole timeline (`would pause=[…]`, `would resume=[…]`, `effective=PENDING` = blips the debounce absorbed). `GET /signal` (agent key, from inside the container) shows the last 50.
5. Judge: right (real pressure) or wrong (blips)? Flapping? UNKNOWN periods (writer down)? The early episodes (12:48–12:54Z) were partly caused by my own builds/tests; the later quiet hours are the better baseline.

## 🐛 WHAT THE LIVE RUNS FOUND (all fixed + pushed; none catchable in the sandbox)

1. `b44c2505` — `crew-orchestrator/main.py` relative import → every `/execute` returned 500 (pre-dates HyperCrew).
2. `9f8b06b7` — dashboard sent the master API key; core's `/operator/*` needs a human JWT → now a 30-day JWT in gitignored `secrets/dashboard_service_jwt.txt`.
3. `b13383b9` + `95940dad` — `coder-agent` returned canned mock answers; core now refuses results flagged `mocked` (my first version only checked the top level; the flag is nested at `result.mocked`).
4. `5fb103c0` — core's `_TEXT_KEYS` lacked `code`, so a real answer was refused as "empty".
5. `9d9e8e6e` — `coder-agent`'s keyword shortcuts fired on every crew task.
Also: the dead default model (NIM 410); my wrong claim "an echo can't fake a PASS" (fixed in core `34ba1667` and at the agent `8043d355`); and today's Shepherd name-key mismatch and verifier leniency (above).
The other Claude session also pushes to this branch: **always `git fetch` first**, re-run tests after a rebase.

## 🧠 GOTCHAS LEARNED (cost real time)

- **Gate heavy steps on the guard's exit code, in the same command:** `python scripts/ram_guard.py --for build && <heavy step>`. The **Windows host** running out of RAM hung Docker while `wsl -e free -m` looked fine.
- `!` in the Claude Code prompt runs **Git Bash**; `free -m` → `wsl -e free -m`; `MSYS_NO_PATHCONV=1` (and `export` it). The console is cp1252: keep script output ASCII. The tool layer **halves backslashes** in shell/Python heredocs: use the Edit tool or `chr(92)` for regexes.
- **Never** show `docker compose config` (expands `.env` secrets; use `-q`). A token must never be printed; scan files for `eyJ…`/`nvapi-`/`sk-` before every commit. The auto-mode classifier blocks reading/writing credentials by design — prepare a script and have the user run it with `!` (that is how the rotation was done).
- Core signs JWTs with **`HYPERCODE_JWT_SECRET`** (= `secrets/jwt_secret.txt`), not the `.env` `JWT_SECRET` line (a different, unused value). The dashboard **caches** its token in memory → restart it after re-minting.
- **Mutation-check your tests, and verify the mutation actually applied** (twice today a "mutation" silently didn't, so the green proved nothing). When appending to a test file from a shell, assert the test count changed.
- Don't use `compose down` to stop things; stop by name. `docker pause` frees no RAM. Core runs `alembic upgrade head` before uvicorn. `crew-orchestrator` and `qa-engineer` source is **bind-mounted** (restart, no rebuild); `coder-agent`, core and `safety-shepherd` (`capabilities.json` baked in) are images (rebuild). Check for 0 active crew runs before restarting a crew component.
- The Shepherd `_agent_caps` lookup is exact → hyphen/underscore variant → `*`; test with the REAL hyphenated names. A reasoning model returns a `thinking` block before `text`: read only `text`, allow `max_tokens` ≈ 1500.
- A scheduled job in this Claude session only fires while the session is open and idle; the Task Scheduler job is the durable one.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
