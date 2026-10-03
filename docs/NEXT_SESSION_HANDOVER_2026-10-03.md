# 📋 NEXT_SESSION_HANDOVER — 2026-10-03 (HyperCrew: first Docker run)

> **🎉 UPDATE 12:55 UTC 2026-10-03 — THE HAPPY PATH HAS RUN.** Guard **ALLOW** → Quest Settler (20 XP, 10 coins, achievement) → Scribe draft → handover gate (skipped) all proven live on Docker with a capable model
> (fcc-proxy → `nemotron-3-ultra-550b-a55b`). Run `b01b22bc-…`; details in `WHATS_DONE.md` (12:50 entry). **Everything below that says "ALLOW unproven" / "needs a builder model" is the earlier snapshot, now superseded.**
>
> Bro, short version (earlier snapshot): **HyperCrew is deployed and proven on Docker.** Two real bugs found and fixed. The **happy path had not
> run yet** because the crew agents aren't running. Live status beats this file; `WHATS_DONE.md` beats everything.
> Branch `claude/focused-darwin-ljrs8k` · draft PR #547 · HEAD at wrap-up is the docs commit after `9f8b06b7`.

---

## 🟢 LIVE STATE RIGHT NOW

| Thing | State |
|---|---|
| `hypercode-core` | new HyperCrew build, healthy, RestartCount 0 (restarted once on purpose for the proof, 22:17 UTC) |
| `hypercode-dashboard` | new build + JWT secret, healthy, RestartCount 0 |
| `crew-orchestrator` | healthy, RestartCount 0, fixed import (restarted 22:26 UTC) |
| `safety-shepherd` | healthy; ALLOW for crew build/verify/publish |
| Migration `023` | applied (`alembic current` = 023 head; `quest_settlements` exists) |
| `coder-agent`, `qa-engineer` | **RUNNING since 2026-10-03 00:17 UTC** (healthy, RestartCount 0) — started on request after the first handover |
| Observability stack (12 containers) | **STOPPED** by me to free RAM (was 853 MB free → ~1.9 GB). Restart = your call |
| RAM | ~1917 MB available (WSL cap 4 GB — never raise it) |

## ✅ WHAT RAN (exact lines in `WHATS_DONE.md`)

Step 0 pre-flight (stop rule hit, fixed by stopping obs) · Step 1 rebuild + swap · Step 2 `alembic current` = `023 (head)`, table
`True` · Step 3 Shepherd ALLOW ×3 · Step 4 `PHASE0 PASS` (29/29), phase1 (3/3), real `docker restart hypercode-core`, **`PHASE2 PASS`**
(9/9, FAILED CLOSED branch) · Step 5 dashboard `/ide` **5/5**.

## 🐛 TWO REAL BUGS (fixed + pushed)

1. `b44c2505` — `crew-orchestrator/main.py` relative import → **every `/execute` was HTTP 500**. Pre-existing since 2026-09-01, on `main` too.
2. `9f8b06b7` — dashboard sent the master API key; core's `/operator/*` needs a human JWT → Morning Card / Pause / Calm Card all 502.
   Now a 30-day JWT in `secrets/dashboard_service_jwt.txt` (gitignored). **Expires ~2026-11-01 — rotate (runbook §8).**

## ⚠️ OPEN — NEEDS A DECISION FROM YOU

- **Exposed 10-year admin JWT.** `.env` line 214 `DASHBOARD_SERVICE_JWT` (user 9, superuser, exp 2036) was printed into the
  session transcript by my mistake. Also injected into `hypercode-core` and `postgres` containers (accidental?). Fix = rotate
  `JWT_SECRET` (kills every token incl. the 30-day one → re-mint) and delete that `.env` line. **Not done.**
- **Earlier leak in git history:** commit `f1edc13e` says `.claude/settings.local.json` "contained a gateway token". Untracking does not
  remove it from history on the pushed branch. Rotate that token if it was ever real.
- **Permission rule you added** (`/permissions`) for the mint command `Bash(cd … && docker exec -i hypercode-core python - < * > secrets/dashboard_service_jwt.txt)`.
  Remove it when you're done minting.
- Obs stack: restart it, or leave it off? (Needs ~1+ GB; the 4 GB ceiling is tight.)
- D1–D12 decisions, kill-switch compose wiring, real GitHub token for the Scribe: all still open, untouched.

## ⛔ UPDATE (12:35 UTC) — capable model wired (`10c0dac8`) but the live proof was STOPPED: host out of RAM

Built an opt-in capable builder/verifier path (fcc-proxy → `nemotron-3-ultra-550b-a55b`; the old default `…super-120b` hit end-of-life 2026-10-03 09:00Z → HTTP 410). A realistic build prompt returned a real unified diff in 9.8 s.
**Then the Windows host ran out of RAM** (1 MB free of 7,974; Memory Compression 4,511 MB; WSL swap ~1.1 GB) — Docker calls hung and every container read *unhealthy* (healthcheck timeouts, no unexpected restart seen). I stopped (stop rule),
started nothing else, and `fcc-proxy` is down (exit 137). **First thing next session: check `wsl -e free -m` AND Windows free memory, close heavy apps / restart Docker Desktop (your call), wait for the containers to go healthy, then
start the proxy and re-run phase1→restart→phase2** (commands in `WHATS_DONE.md` 2026-10-03 midday). `coder-agent`/`qa-engineer` were left running with the proxy ON (`CREW_LLM_BASE_URL` is empty by default — opt-in, it sends crew text to NVIDIA).

## ✅ UPDATE (01:10 UTC) — qa-engineer is now a real verifier (`8043d355`)

Rules (empty / not-a-diff → FAIL) + model review, never invents a PASS, strips smuggled `VERDICT` lines, fails closed. 20 tests (mutation-checked). Live: guard fails ONLY on `verifier_verdict: FAIL`
(5/6 checks PASS) — the builder's output is the prompt parroted back, not a diff. **Blocker for ALLOW is now the builder model**, not the verifier. **Correction to my earlier claim:** "an echo can't fake a PASS" was
wrong when the builder writes its own `VERDICT: PASS` line — fixed in core by the other session (`34ba1667`) and **now deployed** (core rebuilt at `79b5be99`, 02:05 UTC, with `a2ee4530` too; verified in the container, phase0 PASS); my verifier also closes it at the agent.

## 🏁 UPDATE (00:45 UTC) — FIRST REAL COMPLETED RUN

`PHASE2 PASS`: **COMPLETED with a guard verdict = BLOCK** (evidence bundle hash present). Four more bugs found + fixed on the way (orchestrator import; mocked results incl. the nested-flag miss;
`code` key; coder-agent keyword shortcuts firing on every crew task) — see `WHATS_DONE.md`. **BLOCK is correct:** `qa-engineer` has no model (echo stub), so the verify verdict is `UNKNOWN`.
**Unproven:** guard ALLOW → settle/XP → Scribe → handover gate → publish. **Next:** a real verifier for the verify stage. The text below this section is the earlier 00:30 snapshot, kept for the trail.

## 🔁 (00:30 UTC) — agents started, phase 2 re-run

`PHASE2 PASS` (9/9) again, still **FAILED CLOSED**, now "agent returned an empty result". Cause: the proof goal contains the word **"health"**, which
`coder-agent`'s keyword router turns into a **hard-coded mock** (`analyze_system_health()`); core refused it only because the mock's keys aren't text keys.
**Fixed + deployed + live-proven** (`b13383b9`, `95940dad`): the agent flags its mocks, core refuses them; live reason is now "agent result was mocked, not real". (My first version only checked the
top level — the live proof caught it; the flag is nested at `result.mocked`.) **A SECOND bug blocks the happy path:** `coder-agent`'s real Ollama reply is `{status, code, model}` and `code` isn't in
core's `_TEXT_KEYS`, so a genuine answer is refused as "empty" (strict-xfail test documents it) — **decision needed: add `"code"` to `_TEXT_KEYS`**.
To reach COMPLETED you also need: a goal without trigger words (health/metrics/deploy/docker/todo list) and a model that fits RAM (`tinyllama` ≈ 640 MB vs `qwen2.5:3b` ≈ 2 GB; the 4 GB
WSL cap + ~1.9 GB free is tight — check RAM first, stop rule 1.2 GB). See `WHATS_DONE.md` 2026-10-03.

## ❌ NOT PROVEN

- ~~Happy path~~ **PROVEN 2026-10-03 12:50 UTC** (`build → verify → guard ALLOW → settle/XP → Scribe → handover gate (skipped)`). Still unproven: real GitHub publish, the verifier's leniency (PASS with 5 problems listed).
- Second Shepherd path `safety_client.check_dispatch` (strict, mutation agents like `coder-agent` are unregistered → deny-first MUTATION) — never run live; could fail.
- Pause everything with a *running* run ("Saved… / Paused (n) · Resume") — only the "nothing running" text seen.
- Real GitHub PR publisher (never touched). `tests/test_safety_contract.py` (crew-orchestrator) won't collect — not investigated.

## 🧠 GOTCHAS LEARNED

- `!` in this Claude Code prompt runs **Git Bash**, not PowerShell. `free -m` → `wsl -e free -m`. Git Bash mangles `/app` → use `MSYS_NO_PATHCONV=1`.
- **Never** show `docker compose config` output — it expands `.env` secrets. Use `-q`.
- `docker stop` on obs containers can say "zombie, can not be killed" yet free the RAM. Don't use `compose down` (can take core).
- Core runs `alembic upgrade head` before uvicorn: a bad migration = restart loop. First boot after the old stack can take minutes under RAM pressure.
- `crew-orchestrator` source is bind-mounted: edit + `docker restart crew-orchestrator`, no rebuild.
- The auto-mode classifier blocks writing to `secrets/`; the user runs it or adds a narrow permission rule.
- `serviceAuthHeader()` reads `DASHBOARD_SERVICE_JWT` **before** `DASHBOARD_SERVICE_JWT_FILE`.

## ▶️ NEXT TASK (one sentence)

**UPDATE 13:55 UTC: throttle-agent is DEPLOYED in observe mode WITH the debounce (`85da2367`; seen working live: 1st AMBER = PENDING, 3rd consecutive = would-pause tier 6; nothing actually paused).** Next: let observe run and review `GET /signal` / the log (the machine was trending toward RED at 13:55: compression 3,382 MB), and only then consider `enforce`; also decide on fixing `evolve-relay`'s missing `env_file`. (Older text follows.) Deploy the fixed throttle-agent in OBSERVE mode once `python scripts/ram_guard.py --for build` is GREEN (the guard went RED again at 13:15 UTC: host 66 MB free, compression 4.2 GB, while WSL looked fine): start the host writer (`python scripts/ram_guard.py --loop 30 --skip-docker --json --out ram-signal/ram.json`), rebuild + start `throttle-agent` (steps in `WHATS_DONE.md` 13:20), then review `GET /signal` for a while before ever setting `THROTTLE_MODE=enforce`. The RAM guard (13:05) and the throttle-agent code + 57 tests (13:20) are DONE. Runner-up decision: should the verifier be stricter (it PASSed with 5 problems listed)? (The happy path is PROVEN; the real builder/verifier model is wired, opt-in via `CREW_LLM_BASE_URL`.)

---

> 🐶♾️ Built by @welshDog · Llanelli, Wales
> *"Stop apologising for your brain. Start building."*
