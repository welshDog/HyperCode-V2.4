# 📋 NEXT_SESSION_HANDOVER — 2026-10-03 (HyperCrew on Docker, hardened and measured)

> Current as of **2026-10-03 ~19:35 UTC**, verified live. Branch `claude/focused-darwin-ljrs8k` · draft PR #547. `WHATS_DONE.md` has the full detail and every exact proof line; live status beats this file.
> Rewritten as one clean document: every dated "UPDATE"/"RESOLVED" patch it had accumulated is folded in (history is in `WHATS_DONE.md` and `git log`).
> ⏱️ **Time labels:** this machine runs BST (UTC+1). Labels written before ~14:15 UTC in the older docs mix docker/UTC and local clock times; labels from 14:05 UTC on were checked against commit times and container timestamps. **Git commit times (`%z`) and `docker inspect` are authoritative; true UTC = local − 1 h.**

---

## 🎉 THE SHORT VERSION

- **HyperCrew runs on Docker, end to end:** plan → approve → seal → build → verify → guard → settle → scribe → handover gate (always skipped in tests: **no PR can open, no GitHub token is configured**). Proven across a real core restart (run `756625dd`, guard **ALLOW**).
- **Real model:** `fcc-proxy` → NVIDIA NIM `nemotron-3-ultra-550b-a55b` for builder and verifier. **Opt-in** (`CREW_LLM_BASE_URL`); it **sends crew text to NVIDIA**. NIM's free tier is **intermittently overloaded** (HTTP 503 → proxy 529, or bare 500) and its speed swings from 3 s to 100+ s.
- **Measured success rate (live runs, real model):** run 1: 3 of 5 ALLOW; run 2 (with logging): **6 of 10 ALLOW**; 15-run total **9/15 = 60 %**. Every BLOCK was explained from logs: 1 genuine verifier FAIL, 1 builder timeout reported as a build, 2 verifier reasoning-budget exhaustions (UNKNOWN). **The builder and verifier were hardened afterwards (below); one run since: ALLOW in 66 s.** A new, larger rate has NOT been measured yet.
- **Host-RAM safety:** `scripts/ram_guard.py` → Task Scheduler job keeps the signal fresh → **throttle-agent in OBSERVE mode** (pauses nothing; decided: stay in observe).

### What shipped today (all deployed + live-verified unless marked)

| What | Commit | Proof |
|---|---|---|
| HyperCrew first Docker run; 5 live-found bugs fixed | `b44c2505` … `9d9e8e6e` | `prove-crew.py` phases 0/1/2 |
| Real fail-safe verifier + capable-model path (opt-in) | `8043d355`, `10c0dac8` | guard ALLOW → XP → Scribe |
| Host-RAM guard + throttle-agent observe + debounce + Task Scheduler writer | `2748ffbe` … `be4c70f0` | 136 observe decisions, 0 stale, 0 errors, 0 paused |
| IDE health check + fixes (stale run, Pulse real XP, 9 stray containers) | `63f5edd2`, `f83c8321` | live |
| Shepherd applies real grants to hyphenated agent names | `55aea70a` | 0 mismatches across 4 agents × 6 requests |
| **JWT signing secret ROTATED** (exposed 10-year token now 403) | `scripts/rotate_jwt_secret.py` | new token 200, old tokens 403 |
| `evolve-relay` compose path fixed + env trimmed to 7 of 45 vars | `28631576`, `49f0cc6b` | variable NAMES checked, healthy |
| Older `settings.local.json` leak audited: token dead | docs only | 295 local values compared, no match |
| **Verifier**: tightened (PASS must say `none`), two-format prompt, 105 s budget, diagnostic log line, **bounded 5xx retry** | `d78fa0e3`, `29f20038`, `28f88c99`, `d192dcec`, `b04b081c` | 87 tests; retry proven on the real code path with a fake proxy |
| **Builder (coder-agent)**: a failed crew model call is now an **ERROR** (was a nested "completed" build that core read as the diff), bounded 5xx retry, diagnostic log line | `1edf14c5` | 25 tests, 12 mutations caught; core's real `dispatch_to_agent` rejects the new shape; **live ALLOW run `9aa47b8c`** |
| Crew measurement tools | `scripts/measure-crew-run.py`, `scripts/measure-crew-rate.sh` | 15 + 1 live runs |

## 🟢 LIVE STATE (verified 19:30 UTC)

| Thing | State |
|---|---|
| Containers | **36 running, 0 paused, 0 unhealthy**; core, dashboard, orchestrator, coder-agent, qa-engineer, safety-shepherd, fcc-proxy, throttle-agent, healer, evolve-relay all `healthy`, RestartCount 0 |
| `coder-agent` | image **built 19:20Z** (`82839e91d008`, was `7038663b170f`) and **recreated with the proxy ON at 19:26Z** (an earlier recreate at ~19:22Z had lost it, see below), with the builder hardening; **proxy ON** (`CREW_LLM_BASE_URL=http://fcc-proxy:8083`). ⚠️ I first recreated it WITHOUT that variable (compose default is empty = opt-in) and caught it by checking; **any recreate of coder-agent/qa-engineer must pass `CREW_LLM_BASE_URL=http://fcc-proxy:8083` in the shell env** (e.g. `CREW_LLM_BASE_URL=http://fcc-proxy:8083 docker compose --profile agents -f docker-compose.yml up -d --no-deps --no-build coder-agent`) |
| `qa-engineer` | healthy; last restarted 18:56Z; source is bind-mounted (restart picks up code); verifier 105 s budget + retry + `crew_verify` log line live |
| `hypercode-core` | healthy; last started 17:10Z (my deliberate `docker restart` for the end-to-end proof; a healer restart at 14:19Z earlier); **core code was NOT changed today** |
| `throttle-agent` | healthy, `THROTTLE_MODE=observe`; since 12:48Z: **136 decisions** (GREEN 61, AMBER-pending 54 = blips the debounce absorbed, AMBER 18, RED 3), **10 would-pause events** (all tier 6 at AMBER except the early RED ones; the recent ones coincide with my heavy crew-run loops), **0 stale-signal periods, 0 errors, 0 containers ever paused** |
| `evolve-relay` | recreated 17:43 local with the trimmed env (7 vars), healthy |
| Observability stack | **STOPPED** (12 containers; Grafana panel "refused to connect" is expected) |
| Memory (guard, 19:30 UTC) | **AMBER** — host free 611 MB, compression 1,811 MB, WSL available 1,491 MB (it is often AMBER/GREEN-edge now; the harness killed one background probe at low memory). Build floor is 1.5 GB WSL available |
| Git | branch in sync with `origin` after a clean rebase onto the other session's CodeQL tidy-ups; `results/*` shows modified from another process (not mine; never commit it) |

## ▶️ NEXT TASK (one sentence)

**Re-measure the crew success rate with ALL the hardening in place** (`MSYS_NO_PATHCONV=1 bash scripts/measure-crew-rate.sh` with ~10 goals, guard not RED, one at a time) and, for every non-ALLOW, read its `crew_build` / `crew_verify` log line to see whether the cause is now NIM slowness, a genuine FAIL, or something new.

## ⚠️ OPEN — NEEDS A DECISION FROM YOU (nothing here is started)

1. **Core should reject a NESTED agent error (recommended; backend rebuild).** Every agent's base wrapper returns `status="completed"` with the real result nested; core's "agent reported an error" check only looks at the top level. The builder now returns a top-level error, but the **verifier's error path** (timeout, 5xx) still arrives nested, is read as text, and shows up as `verifier verdict: UNKNOWN` (still blocks, but with a misleading label). A one-line defence in `backend/app/crew/dispatch.py` (also treat `result.status == "error"` as an error) fixes it for every agent; it needs a core rebuild (guard GREEN, nothing running).
2. **Reasoning-limit QUALITY probe (untested):** `thinking: {type: disabled}` makes a clean-diff verify ~13 tokens / 1–5 s (vs 336–820 tokens / 14–22 s), but whether it still catches real bugs is UNKNOWN (broken diffs got zero valid answers: NIM was overloaded, then the harness killed the probe for memory). Re-run only when memory is comfortable: baseline vs thinking-off, 5 diffs incl. broken ones, 10 calls, **output written to a FILE not a pipe**, retry on 5xx. Do NOT switch the verifier to thinking-off without it.
3. **throttle-agent `enforce`: decided NO** (Lyndz). Reasons: containers total only ~1.4 GB, `pause` frees no RAM, `stop` frees < ~305 MiB and the healer fights it, tier 6 contains `fcc-proxy` (the crew's model path). Optional, needs a go: remove `fcc-proxy` from tier 6 and log which threshold tripped. Enforce would need a real unforced pressure baseline and the logon/reboot test of the scheduled task.
4. **Core + orchestrator `monitor` → `enforce` for the Shepherd:** never without checking the Safety Feed for ESCALATEs first, and remembering the four agents' real grants now apply (e.g. `devops-engineer` may use docker).
5. **Dashboard token expiry ~2026-11-02:** re-run `MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py` (preflight, then `--yes`) before then. Remove the `/permissions` rule you added for the old mint command if it is still there.
6. **Observability stack:** restart it or leave it off (needs ~1+ GB; the 4 GB WSL cap is tight).
7. Original D1–D12 decisions, kill-switch compose wiring, a real GitHub token for the Scribe (do **NOT** configure one without asking): all still open and untouched.
8. The **unexplained dashboard restart** at 12:50:23Z — worth a look if it recurs. `postgres` still holds a copy of the OLD (dead) JWT secret via `env_file:` until its next recreate (harmless).
9. **Pre-existing, not mine:** `agents/coder/test_coder.py` has 5 failing tests (they predate the agent's auth middleware and get 503/401); my new tests are in `agents/coder/test_crew_build.py`. Fix or retire them deliberately; do not "fix" by loosening.
10. **Housekeeping:** synthetic probe files remain in `qa-engineer`'s `/tmp` (removal not permitted; harmless; gone on recreate).

## ❌ NOT PROVEN

Real GitHub PR publish · dashboard-side approval UI · "Paused (n)" with a *running* run · kill-switch compose wiring · the Task Scheduler job across a logon/reboot · `THROTTLE_MODE=enforce` · **the 5xx retries (verifier AND builder) against a REAL NVIDIA 5xx inside a crew run** (proven with a fake clock/client and, for the verifier, a fake local proxy) · a crew success rate AFTER the hardening (only one ALLOW run since, n=1) · whether limiting the model's reasoning keeps bug-catching · the settlement row for the later ALLOW runs (the settle stage finished; XP/coins were proven on the first ALLOW run).

## 🔭 HOW TO READ WHAT THE CREW IS DOING (new today)

- **Verifier:** `docker logs qa-engineer 2>&1 | grep crew_verify` → one line per verify call: `elapsed`, `stop_reason`, `attempts`, `in_tokens`/`out_tokens`, `max_tokens`, `thinking_chars`, `text_chars`, `reply_verdict` (what the model wrote; `NONE` = no valid `VERDICT:` line), `final_verdict` (`UNKNOWN` = none), `downgraded`. `verifier=retry …` lines show a 5xx retry; `verifier=error …` and `verifier=rules …` show the other paths. `stop_reason=max_tokens` with `out_tokens` = `max_tokens` = the model's hidden thinking used the whole budget.
- **Builder:** `docker logs coder-agent 2>&1 | grep -E "crew_build|LLM proxy"` → `crew_build model=… elapsed=… attempts=… stop_reason=… in_tokens=… out_tokens=… max_tokens=… text_chars=…`; `crew_build retry attempt=N status=529 wait=3s` on a retry; `LLM proxy HTTP 529 (attempt N)` / `LLM proxy request failed: ReadTimeout` on failures (the task then returns an ERROR status).
- **Neither logs** the diff, the model's text, the goal or any token (each pinned by a test).
- **Measure the rate:** one run = `docker exec -e MEASURE_GOAL="…" -i hypercode-core python - < scripts/measure-crew-run.py`; many = `MSYS_NO_PATHCONV=1 bash scripts/measure-crew-rate.sh "goal 1" "goal 2" …`. They ALWAYS reject the handover gate, read the guard verdict + failed checks from the run, and never print a secret. Avoid the words health/metrics/deploy/docker/"todo list" in goals. `scripts/prove-crew.py` phase 2 prints PASS for BOTH ALLOW and BLOCK: read the verdict line.

## 🔭 HOW TO REVIEW THROTTLE-AGENT OBSERVE MODE (read-only)

1. `python scripts/ram_guard.py --for check` — memory now.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status` — writer `Running`, signal age well under 120 s.
3. `docker inspect -f '{{.State.Health.Status}} r={{.RestartCount}}' throttle-agent` and `docker ps --filter status=paused -q | wc -l` (**must be 0**).
4. `docker logs throttle-agent 2>&1 | grep observe_decision` — the timeline (`would pause=[…]`, `effective=PENDING` = blips the debounce absorbed). `GET /signal` from inside the container (its own key, never printed) shows the latest.

## 🐛 WHAT THE LIVE RUNS FOUND (all fixed + pushed; none catchable in the sandbox)

1. `b44c2505` — `crew-orchestrator/main.py` relative import → every `/execute` returned 500 (pre-dates HyperCrew).
2. `9f8b06b7` — dashboard sent the master API key; core's `/operator/*` needs a human JWT → now a 30-day JWT in gitignored `secrets/dashboard_service_jwt.txt`.
3. `b13383b9` + `95940dad` — `coder-agent` returned canned mock answers; core now refuses results flagged `mocked` (my first version only checked the top level; the flag is nested).
4. `5fb103c0` — core's `_TEXT_KEYS` lacked `code`, so a real answer was refused as "empty".
5. `9d9e8e6e` — `coder-agent`'s keyword shortcuts fired on every crew task.
6. **My verifier-tightening regression (`29f20038`):** contradictory prompt wording made the reasoning model ramble to `max_tokens` with no `VERDICT:` line → guard UNKNOWN → BLOCK. Unit tests could not see it; a live probe showing `stop_reason`/usage did.
7. **The builder reported a ReadTimeout as a completed build (`1edf14c5`):** the error sat one level down, core read the error text as the diff, only the verifier's diff rule saved the run (2 of ~17 runs).
8. **NVIDIA NIM overload** (503 → 529/500): the reason is only in the response BODY (the proxy log prints the bare status). Mitigated by the bounded retries.
Also: the dead default model (NIM 410); my earlier wrong claim "an echo can't fake a PASS" (fixed in core `34ba1667` and at the agent `8043d355`).
The other Claude session also pushes to this branch (CodeQL tidy-ups): **always `git fetch` first**, rebase, and re-run tests after it.

## 🧠 GOTCHAS LEARNED (cost real time)

- **Gate heavy steps on the guard's exit code, in the same command:** `python scripts/ram_guard.py --for build && <heavy step>`. The **Windows host** running out of RAM hung Docker while `wsl -e free -m` looked fine. A background job can be KILLED by the harness at low memory: write long probe output to a **file inside the run**, not a pipe, and do not restart a killed job unasked.
- **A killed `docker exec` leaves its process running INSIDE the container:** find it via `/proc/*/cmdline` and SIGTERM that PID (these slim images have no `kill`/`ps`: use `python -c "import os,signal;os.kill(PID, signal.SIGTERM)"`).
- **Recreating `coder-agent`/`qa-engineer` drops the opt-in proxy** unless `CREW_LLM_BASE_URL=http://fcc-proxy:8083` is in the shell env (verify afterwards: `docker inspect` env, the URL only; the token is `CREW_LLM_AUTH_TOKEN`, never print it). `coder-agent` is baked into an image (rebuild + recreate); `qa-engineer` and `crew-orchestrator` source is bind-mounted (restart only); core and `safety-shepherd` are images.
- **Agents wrap every result as `status="completed"`** (base agent): an error dict returned by `process_task` ends up nested. Only a TOP-LEVEL `status: error` (the coder's `execute()` now does this for crew stages) is rejected by core.
- `!` in the Claude Code prompt runs **Git Bash**; `free -m` → `wsl -e free -m`; `MSYS_NO_PATHCONV=1` (and `export` it). The console is cp1252: keep script output ASCII. The tool layer **halves backslashes** in shell/Python heredocs: use the Edit/Write tool or write the script to a file (twice today a patch script silently wrote nothing/garbage).
- **Never** show `docker compose config` (expands `.env` secrets; use `-q`, or pipe `--format json` into a script that prints only chosen fields). A token must never be printed; scan files for `eyJ…`/`nvapi-`/`sk-` before every commit. The auto-mode classifier blocks reading/writing credentials by design — prepare a script and have the user run it with `!` (that is how the JWT rotation and the relay env were done).
- Core signs JWTs with **`HYPERCODE_JWT_SECRET`** (= `secrets/jwt_secret.txt`), not the `.env` `JWT_SECRET` line. The dashboard **caches** its token in memory → restart it after re-minting.
- **Mutation-check your tests and verify the mutation actually applied** (three times a "mutation" silently didn't, and twice a test passed for the wrong reason: a 100 s fake duration tripped a different guard, a fake call that ignored its timeout). A retry test must use fast-failing cases.
- A retry in a time-boxed pipeline must share ONE budget, never start an attempt it cannot finish, and never retry a timeout (core gives up at 120 s; the orchestrator spends a few seconds first).
- Don't use `compose down` to stop things; stop by name. `docker pause` frees no RAM. Core runs `alembic upgrade head` before uvicorn.
- The Shepherd `_agent_caps` lookup is exact → hyphen/underscore variant → `*`; test with the REAL hyphenated names. A reasoning model returns a `thinking` block before `text`: read only `text`, allow `max_tokens` ≈ 1500 (but its speed is only ~20–30 tokens/s, so do not raise it blindly: 105 s timeout).
- A scheduled job in this Claude session only fires while the session is open and idle; the Task Scheduler job is the durable one.

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
