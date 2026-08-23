# 🎯 Active Next Tasks
> Update this every session. Completed items → `WHATS_DONE.md`.
> For sacred rules + architecture → `CLAUDE.md`
> Last updated: **August 23, 2026 (N7/N4/N2/0a/N1/0b all resolved live — see `WHATS_DONE.md`'s 2026-08-23 afternoon entry)**

---

## 🆕 New from 2026-08-22 afternoon session (review_mission fix + broski-coo v1)

> Full write-up: `WHATS_DONE.md`'s 2026-08-22 entry, `agents/broski-coo/HYPER-AGENT-BIBLE.md` §6.

| # | Task | Priority |
|---|---|---|
| N6 | **`.env` location gotcha, bit us twice this session**: `HyperCode-V2.4`'s Docker Compose reads `HyperCode-V2.4/.env`, NOT the parent `HperCore/.env` — both `OPENROUTER_API_KEY` and `HYPERCODE_API_KEY` were dropped into the parent file first and silently had no effect until copied across. Check `grep VAR HyperCode-V2.4/.env` specifically, never assume a key "is set" from the parent workspace file. | 🟡 doc/process gotcha |
| N7 | **✅ RESOLVED, 2026-08-22 evening.** Full-fleet sweep for the same `HYPERCODE_API_KEY`/`AGENT_API_KEY` 503 bug that hit `broski-coo`. Found it live on 6 more agents in `docker-compose.agents-full.yml` — `brain-agent`, `business-agent`, `throttle-agent`, `tips-tricks-writer`, `super-hyper-broski-agent`, `test-agent` — all set `API_KEY=${API_KEY:-dev}` in their env block, but their `base_agent.py`-derived middleware only ever reads `HYPERCODE_API_KEY`/`AGENT_API_KEY`, which never reached the container. Confirmed live before fixing: `/execute` on all 6 returned `503 {"detail":"Agent API key not configured"}` regardless of key. **Fixed**: added `HYPERCODE_API_KEY=${API_KEY:-dev}` to each of the 6 blocks (mirroring the working pattern already used in `docker-compose.agents.yml`'s 6 agents — `project-strategist`/`nemoclaw-agent`/`safety-shepherd`/`broski-pets-bridge`/`healer-agent`/`coder-agent` — which were checked and confirmed correctly wired, not affected). `docker compose config` validated clean, all 6 containers recreated + came back `healthy`, and live-reverified: `no-key`→401, `wrong-key`→401, `real-key`→past-auth (422/404) on all 6 — matches the correctly-wired agents' behavior exactly. **Swept the other 33 live fleet endpoints too** (specialist squad, ghost agents, fleet-controller, mission-director, etc.) — none showed the bug signature. **Separate finding, not fixed (out of scope for N7):** `project-strategist` (`:8001`) is `Exited (255)` — its own compose wiring is correct (was verified fine before the crash), no error in its last logs before exit, needs its own look next session. | ✅ resolved |

---

## 🆕 New from 2026-08-21/22 session (truth registry + mission-director + mission-evaluator)

> Full write-up: `docs/NEXT_SESSION_HANDOVER_2026-08-21-late-night.md`. All
> items below are genuinely new this session — everything in "🔥 Immediate"
> and below is unchanged from 2026-08-20 and still accurate.

| # | Task | Priority |
|---|---|---|
| N1 | **✅ RESOLVED, 2026-08-23 night.** Lyndz rotated `ANTHROPIC_API_KEY` directly in `.env` himself (the one step no agent could do). Recreated every container holding the old dead key (9: `healer-agent`, `hypercode-core`, `broski-coo`, `project-strategist`, `broski-pets-bridge`, `coder-studio`, `evolve-relay`, `fleet-controller`, `mission-director` — `broski-bot`/`evolve-relay` had already picked it up on their own). Verified live: a direct Anthropic call succeeds (real response, not a 401), and `mission-director`'s `POST /api/v1/missions/propose` now returns `200`/`status: "previewed"` with a real Shepherd evaluation (`ESCALATE` for the `docker` category, `execution.performed: false`) — the exact happy path that was blocked on `preview_unavailable` before. | ✅ resolved — [Issue #433](https://github.com/welshDog/HyperCode-V2.4/issues/433) |
| N2 | **✅ RESOLVED, 2026-08-22 night.** Both credentials rotated and verified live. `DASHBOARD_SERVICE_JWT`: re-minted (365-day, via the documented `create_access_token(1, timedelta(days=365))` procedure, never printed to chat — generated inside `hypercode-core`, moved via a local scratch file, applied via a single approved `.env` edit), `dashboard` container recreated, confirmed working end-to-end (`/api/tasks` → `200`). Postgres password: rotated live via `ALTER ROLE` (zero downtime — existing connections unaffected, only new ones need the new password), verified over the network (old password → `InvalidPasswordError`, new → connects), `.env` updated (`POSTGRES_PASSWORD`, `DB_PASSWORD`, `DATABASE_URL`). **Two real gaps found and fixed along the way, not just the headline rotation:** (1) `hypercode-core` and `celery-worker` don't read `DATABASE_URL` at all — they use `HYPERCODE_DB_URL`, built from `${POSTGRES_PASSWORD}` via compose substitution, which the first dependency sweep (grep for `DATABASE_URL` only) missed entirely; both needed a recreate to pick up the new password, same as the other 9. (2) HyperHealth's seeded `postgres-db-health` check (`agents/hyperhealth/seed_checks.py`) stores a **literal DSN, password included, as a DB row** — not reactive to `.env` changes at all. Rotating the live password without re-seeding left it retrying every 30s with the dead password (visible as a steady flood of `password authentication failed` in Postgres's own logs, traced to `hyperhealth-worker` specifically via `client_addr`). Fixed by re-running `seed_checks.py --force`; also fixed a real bug hit doing that — the script's `.env` reader had no explicit encoding and crashed on a non-cp1252 byte (same trap class as other Windows encoding issues in this repo), now opens with `encoding="utf-8"`. **Any future Postgres password rotation must re-run this script too** — it's a second source of truth for the DSN, not derived live from `.env` at check-execution time. Real incident during this work, not just a close call: recreating ~12 containers on top of an already-running 69-container fleet drove the host to `0.40GB` free and took the whole WSL2 VM unresponsive — recovered via a Docker Desktop restart + staged relaunch, zero data loss, zero unhealthy after. See `docs/STATUS.md`'s corrected "Known Risks" entry. | ✅ resolved — [Issue #434](https://github.com/welshDog/HyperCode-V2.4/issues/434) |
| N3 | **✅ RESOLVED, 2026-08-22 (commit `378b336d`).** `review_mission` now reads `plan_response.safety.decision` before allowing approval: `BLOCK` hard-rejects (`409`), no override exists; `ESCALATE` requires a non-empty `escalation_reason` (`422` without one), audited in the Governance Ledger — no silent downgrade to `ALLOW`. 13/13 tests pass. | ✅ resolved |
| N4 | **✅ RESOLVED, 2026-08-22 evening.** Root cause was NOT a YAML bug in `broski-bot` (or any service) — it was a bad invocation pattern: `docker-compose.yml` already pulls `docker-compose.core.yml` in via `include:`, so passing `-f docker-compose.core.yml` a second time (as the exact repro command in #435 does) merges every one of that file's services with itself. List-type fields like `security_opt` get concatenated onto their own duplicate, which Compose then rejects. **Proved, not assumed**: reproduced the exact error with the double-`-f` command, confirmed it hits whichever service validates first (`hypercode-core`, `celery-worker`, `broski-bot` — all three seen depending on which profiles/files are combined), then confirmed both real launch patterns — `AGENT-START.md`'s documented command and `hyperlaunch.ps1`'s canonical 4-file set — already resolve clean, because neither double-passes `core.yml`. Found the one place in the repo that models the broken pattern: `cleanup-and-prepare.ps1`'s "Recommended startup command" (stale, predates the include-based `docker-compose.yml`) — fixed to point at `hyperlaunch.ps1` instead. Added a guard comment to `docker-compose.yml`'s `include:` block so this doesn't get reintroduced. Nothing in `docker-compose.core.yml` itself needed changing. | ✅ resolved — [Issue #435](https://github.com/welshDog/HyperCode-V2.4/issues/435) |
| N5 | **`docs/NEXT_TASKS.md` (this file) and `docs/STATUS.md`** — `STATUS.md` still predates the 08-19/08-20 reconciliation (banner-only fix again this session, no full rewrite — same reasoning as last time: a rushed rewrite risks re-creating the duplication bugs it would need to avoid). | 🟡 doc debt, carried forward |

---

## 🔥 Immediate — Do These First

> ✅ **"Launch 25-agent fleet" below has NO remaining known blocker.** Item #9 (every
> agent's container-internal port matching compose's uniform `HOST:8080` mapping,
> including the 3 that couldn't even build) closed 2026-08-20 late evening (commit
> `84fa5a2d`). **Item #0 (the last blocker) is now also resolved, same night**: 13 of
> ~24 agent names that used to be duplicated between `agents-full.yml` and
> `docker-compose.agents.yml` are deleted from `agents-full.yml` for good —
> `agents.yml`'s versions (the real, live, hardened ones) are the sole definition for
> all 13. Verified via `docker compose config` with both files: zero collisions. See
> item #0 below for the full writeup.

| # | Task | Priority |
|---|---|---|
| 0 | **✅ RESOLVED FOR REAL, 2026-08-20 late evening.** Re-derived the overlap directly from each file's `services:` block (not a broader `comm` sweep across the whole include chain, which is how the original "14" count included 2 spurious network names) — found **13 real overlapping agent names**: `crew-orchestrator`, `coder-agent`, `backend-specialist`, `frontend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`, `goal-keeper`, `project-strategist`, `agent-x`, `hyper-architect`, `hyper-observer`, `hyper-worker`. Compared both files' definitions for each: `docker-compose.agents.yml`'s versions are the real, live, hardened ones (e.g. `crew-orchestrator` has volume-mounted live code, the HYPER-SILLs loadout, `security_opt`, real API-key wiring) — `docker-compose.agents-full.yml`'s copies were leaner stubs that had never actually been composed up. **Decision: `agents.yml` stays canonical for all 13 — their duplicate blocks are deleted from `agents-full.yml` for good.** `agents-full.yml` is now a clean 11-agent ghost-only overlay (`brain-agent`, `business-agent`, `coderabbit-webhook`, `hyper-split-agent`, `session-snapshot`, `super-hyper-broski-agent`, `system-architect`, `test-agent`, `throttle-agent`, `security-engineer`, `tips-tricks-writer`). **Verified via `docker compose config` with both files + `--profile agents --profile hyper`**: no errors, 46 services resolved, and the merged `crew-orchestrator` definition confirmed to be the real hardened one (grepped for `volumes`/`security_opt` in the resolved output), not a stub. **A second, independent bug found and fixed in the same pass**: `agents.yml`'s `project-strategist` pointed at `agents/business/project-strategist` — a directory whose Dockerfile/code was deleted the same day by the business-agent fix (commit `0c2f4fd6`), leaving only stray untracked bind-mount folders (`hive_mind/`, `memory/`, `shared/`, `src/`). Repointed to the real `agents/08-project-strategist`, which turned out to have its *own* separate, pre-existing bug — missing `base_agent.py` entirely (every sibling numbered agent 01–07/09 has one; `agent.py` imports it and would `ModuleNotFoundError` on boot). Copied the same clean template used for brain-agent/business-agent (from `agents/09-tips-tricks-writer`), added the missing `COPY base_agent.py .` to the Dockerfile, and aligned `requirements.txt` (was missing `httpx`/`anthropic`/`openai`, all used by the copied template). **Verified by building + running standalone**: `docker build` succeeded, `docker run` + `curl /health` → `{"status":"healthy","agent":"project-strategist"}` (200). **Separate finding, NOT fixed (out of scope for item #0, logged as a new item below):** `agent.py`'s `plan()`/`delegate_tasks()` methods (the actual specialist-delegation logic this agent exists for) use the old synchronous-client style — `self.client.messages.create(...)` and `self.redis.hset(...)` both called without `await` against the new async client/redis — and reference `self.config.core_url`, which doesn't exist on `AgentConfig`. Worse: `ProjectStrategist` never overrides `process_task`, so `/execute` silently falls through to the generic inherited handler and `plan()`/`delegate_tasks()` are unreachable dead code — the container boots and answers requests fine, it just doesn't do real task delegation. See item #0a below. | ✅ resolved |
| 0a | **✅ RESOLVED, 2026-08-23 night.** `agents/08-project-strategist/agent.py`'s `plan()`/`delegate_tasks()` were dead code — fixed all 3 root causes: (1) `ProjectStrategist` now overrides `process_task` (preserving the base class's approval-gate check) to generate/derive a `task_id` and call `plan()` — `/execute` reaches real planning logic instead of the generic LLM passthrough. (2) `plan()`'s LLM call and both `self.redis.hset(...)` calls now correctly `await` (previously synchronous calls against async clients — Anthropic/Ollama's `.messages.create()` and `redis.asyncio`'s `.hset()` are both coroutines); `self.redis` calls are also now guarded with `if self.redis:` since it can be `None` if Redis was unreachable at startup. (3) `self.config.core_url` (never existed on `AgentConfig`, would've raised `AttributeError` the first time `plan()` ran) replaced with `os.getenv("CORE_URL", "http://hypercode-core:8000")` — `CORE_URL` was already correctly set in `docker-compose.agents.yml`, just never read. `plan()`'s signature changed from taking a `TaskRequest` object to `(task_id, task, context)` primitives, matching what `process_task` naturally has — no other caller in the repo used the old signature (checked: only an HTTP-level integration script exists, `tests/test_orchestrator_strategist_integration.py`, unaffected). **Verified live, not just read**: the container is bind-mounted (`./agents/08-project-strategist:/app`), so a plain `docker restart` picked up the fix with no rebuild. In-process test (constructing the real `ProjectStrategist` object inside the running container, monkeypatching only the LLM client to the Ollama fallback since `ANTHROPIC_API_KEY` is still invalid per N1) proved the full await chain now works — `process_task` correctly reaches `plan()`, which correctly awaits the LLM call all the way to a real HTTP request landing at Ollama (failed only on an expected, unrelated model-name mismatch: Ollama doesn't have any Claude models pulled). **Follow-up, 2026-08-23 night, once N1 unblocked the real key**: re-ran the full happy path for real and found (and fixed) 3 more real bugs the earlier partial test couldn't reach: (1) `agents/08-project-strategist/Dockerfile` baked `ENV AGENT_MODEL=claude-3-opus-20240229` — a retired model, 404 on every real call, silently masked before because the key itself was invalid first. Removed the override entirely so it falls through to `AgentConfig`'s own default (`claude-sonnet-4-6`, confirmed live-valid). (2) Claude reliably wraps its JSON response in a ` ```json ` fence (sometimes with trailing prose after the closing fence) despite the prompt asking for raw JSON — `json.loads()` on the raw text always fell back to `{"raw_plan": ..., "tasks": []}`. Fixed by locating the fenced block instead of assuming the whole string is JSON. (3) `SPECIALIST_AGENTS`'s hardcoded ports were stale for 3 of 7 (`frontend-specialist` moved to `:8012`, `security-engineer`/`system-architect` moved to the uniform `:8080` during the 2026-08-20 port audit, item #9 above — this dict was never updated), and `delegate_tasks()` sent no auth header at all, so even a correct port would 401. Both fixed. **Verified live, for real this time**: a full `process_task` call produced a real, correctly-parsed 9-task structured plan (`feature_name`, `complexity`, dependencies, acceptance criteria all present) via a genuine Claude call, and `delegate_tasks()` completed without error against the corrected port+auth. **New, separate finding, not fixed (own item, not 0a's scope):** `frontend-specialist` (and likely the other 6 specialists — not individually checked) has **no `ANTHROPIC_API_KEY` in its own compose env at all** — its own LLM call fails with a generic "Connection error" rather than falling back cleanly. See item 0b below. `project-strategist`'s earlier `Exited (255)` (found 2026-08-22 afternoon) has not recurred since the 2026-08-22 night full-fleet restart — 0 restarts, stable since. | ✅ resolved |
| 0b | **✅ RESOLVED, 2026-08-23 afternoon.** Confirmed the suspicion from the night before: all 7 specialist agents (`frontend-specialist`, `backend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`, `security-engineer`, `system-architect`) had **no `ANTHROPIC_API_KEY` in their compose env at all** — `docker exec frontend-specialist printenv ANTHROPIC_API_KEY` → empty, `/execute` still `200` but the LLM call inside failed with a generic "Connection error." Added `ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}` to all 7 blocks (5 in `docker-compose.agents.yml`, 2 — `security-engineer`/`system-architect` — in `docker-compose.agents-full.yml`). **Second bug found once the key was live**: all 7 agents' `Dockerfile`s bake the exact same retired model, `ENV AGENT_MODEL=claude-3-5-sonnet-20241022` (a systemic copy-paste across the whole specialist-squad template, confirmed via `grep -r` — `agents/brain` and `agents/business`'s Dockerfiles correctly use `claude-sonnet-4-6`, only the 7 numbered specialists have the stale one). Removed the override from all 7 Dockerfiles so they fall through to `base-agent/agent.py`'s own default (`claude-sonnet-4-6`, already confirmed live-valid during N1's verification). **Rollout finished, all 7 rebuilt + recreated + confirmed live** (`AGENT_MODEL` reads `None` on every one). **Third bug, caught mid-rollout**: `security-engineer`/`system-architect` have an explicit `image:` override (`hypercode-security-engineer:latest`/`hypercode-system-architect:latest` — no `v24`) unlike the other 5 (no `image:` field, Compose's own `<project>-<service>` default naming happens to equal `hypercode-v24-<service>`) — the first rebuild pass used the uniform `hypercode-v24-<name>` tag for all 7, which silently built an orphan image for these 2; `docker compose up --force-recreate` (no `--build`) just reused the old stale image under the real tag. Caught by re-checking `AGENT_MODEL` after recreate instead of trusting the step alone; rebuilt both under their real tags, fixed. **Verified live, full end-to-end delegation chain**: real `project-strategist` `/execute` call → real 4-task plan → `delegate_tasks()` fired real HTTP calls to `backend-specialist`(×2)/`qa-engineer`/`devops-engineer`, all `200 OK` with genuine LLM-generated implementation plans, confirmed in each specialist's own logs. **Real gotcha hit while doing this, worth remembering**: wrapping `docker build`/`docker compose build` in an explicit `timeout N` (100–180s) silently kills these builds before they finish (they're genuinely slow — apt-get installs gcc/docker-cli from scratch) while still reporting a misleading "completed, exit code 0" from the outer shell — the image tag is left pointing at the old content with no error surfaced. Fix: never wrap these in an inner `timeout`; let the harness's own 120s auto-backgrounding handle it, or use a much larger explicit value (600s+). **Separate, unrelated finding, not investigated**: restarting `frontend-specialist`/`backend-specialist` created a stray file named literally `:memory:.ses` in their bind-mounted directories — looks like a pre-existing bug where some session/cache store's default `:memory:` SQLite DSN gets misused as a real filename. Left untracked, not chased. Also hit, unrelated: `project-strategist` had silently exited (`Exited (255)`, no error, same signature as the still-unexplained 2026-08-22 recurrence) sometime before this session started — `docker start` recovered it cleanly. | ✅ resolved |
| 0b | **3 more real bugs found during the actual first fleet launch attempt, 2026-08-20 (all fixed same session):** (1) `agent-x`/`hyper-architect` (both `context: .` in `agents.yml`) hit the exact same `.dockerignore` gap the `hyper-observer`/`hyper-worker` fix covered earlier — `/agents/` is broadly excluded and only `observer/`/`worker/` had carve-outs; added `architect/`/`agent-x/` too. (2) `agents-full.yml`'s `test-agent` used `context: ./agents/test-agent`, but its Dockerfile `COPY`s a sibling `shared/` (the real `agents/shared/agent_utils.py`, a direct import) unreachable from that context — broadened to `context: ./agents`, `dockerfile: test-agent/Dockerfile`. (3) **The big one**: all 11 of `agents-full.yml`'s own ghost agents referenced networks `app-net`/`agent-net` (singular) that were never created **anywhere** in the real stack — only `agents-net`/`data-net`/etc. (with an `s`, defined for real in `docker-compose.core.yml`) actually exist. Every one of those 11 agents could build an image but could never actually start a container. Fixed via `replace_all` across all 11 service blocks: `[app-net, agent-net, agents-net]` → `[agents-net, data-net]`. Also found: `project-strategist` had a **stale cached image** from before the item #0 context repoint — `docker compose up -d` doesn't rebuild automatically, so it kept running old code (`python: can't open file '/app/src/main.py'`, crash-looped) until an explicit `docker compose build project-strategist` was run. **All fixed, verified, and the fleet is now actually launched and healthy** — see item #2. | `.dockerignore`, `docker-compose.agents-full.yml` |
| 1 | ~~Verify no port clashes~~ ✅ Done 2026-08-20 morning pass — found 3; ✅ **all fixed** across the full 2026-08-20 evening (see Completed tables). Final tally: `system-architect`, `hyper-split-agent`, `session-snapshot`, `tips-tricks-writer`, `test-agent` all moved off colliding ports. The launch command's missing `--profile agents` flag is now documented as required. **Correction:** an earlier pass in this same session mis-filed `test-agent` as one of the item-#0 same-name-merge cases — re-checked directly against the true base-include file set and it was never in that list, just a plain port collision (same class as `tips-tricks-writer`). Fixed accordingly, no architecture decision needed for it. | ✅ all fixed |
| 2 | **✅ LAUNCHED, 2026-08-20 late evening.** `docker compose --profile agents --profile hyper -f docker-compose.yml -f docker-compose.agents-full.yml up -d` run for real. Hit and fixed 3 more launch-time-only bugs along the way (item #0b) that no amount of `docker compose config`/standalone `docker build` verification could have caught — they only surfaced when containers actually tried to start together (missing dockerignore carve-outs, a too-narrow build context, and phantom network names). One transient `hypercode-core` restart mid-launch (heavy concurrent build/startup load) cascaded a few "dependency failed to start" errors — re-ran `up -d` once it recovered and everything came up clean. **Final state: all 25 agents live, zero unhealthy containers anywhere on the box** (67 total running). | ✅ done |
| 2a | **✅ FIXED, 2026-08-20 late evening.** `throttle-agent` was crying "Error while fetching server API version... No such file or directory" — it talks to the Docker daemon via `docker.from_env()` (pause/unpause containers for rate limiting) but had no way to reach it. Found `docker-compose.agents.yml` already runs a dedicated `docker-socket-proxy-healer` service whose own comment literally says "ONLY for healer + throttle-agent" — the infrastructure existed, throttle-agent was just never wired to it. Added `DOCKER_HOST=tcp://docker-socket-proxy-healer:2375` + a `depends_on` (mirroring `healer-agent`'s exact pattern) — never mounted `/var/run/docker.sock` directly, keeps the Sacred Rule's spirit (scoped proxy, not raw socket access). **Verified live**: `curl /health` → `{"status":"healthy","agent":"throttle-agent","docker":"ok","healer_ok":true,...}` (was `"docker":"error"` before). See item #2b for a second, separate throttle-agent finding this fix surfaced more clearly (Docker noise was drowning it out before). | `docker-compose.agents-full.yml`'s `throttle-agent` block |
| 2b | **New, not fixed — needs a decision, not a wiring fix.** `throttle-agent` logs `[Throttle] MemStream unreachable: All connection attempts failed` every 10s. `MEMSTREAM_URL` (`agents/throttle-agent/main.py`) defaults to `http://127.0.0.1:8010` — inside the container that only ever points at itself, never another service, so it's a non-functional placeholder unless overridden. There is no "MemStream" service defined anywhere in this compose stack (checked all `docker-compose*.yml`). **This is a real, planned component, not dead code**: `agents/broski-bot/src/cogs/ai_relay.py` + `slash_ask.py` also depend on it — a "local MemStream AI" the bot's `/ask` command streams tokens from (`MEMSTREAM_API_URL`, defaults `:8011` — a *different* port/env-var convention than throttle-agent's, another inconsistency to reconcile if it gets built). Unlike item #2a's Docker socket (real infra existed, just unwired), this is a genuinely missing dependency — never deployed anywhere. Needs Bro's call: build the MemStream service for real (and reconcile the two different port/env-var conventions expecting it), or strip the polling code out of both consumers. Not fatal in either agent — background polling loops, HTTP healthchecks unaffected. | `agents/throttle-agent/main.py`, `agents/broski-bot/src/cogs/{ai_relay,slash_ask}.py` |
| 2c | **✅ BUILT, 2026-08-20 late night.** `fleet-controller` Phase 0 shipped — the first piece of the mission-director/fleet-controller architecture (Approach C: an LLM planner with zero mutation authority, a deterministic controller with zero LLM access). Spec: `docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`. New minimal FastAPI service (`agents/fleet-controller/`, :8094, behind a new `--profile fleet` — not part of the standard `--profile agents --profile hyper` launch), no Docker socket, no `DOCKER_HOST`, no crew-orchestrator credential, no LLM client. Fails **closed** (unlike `safety_gate.py`'s deliberate fail-open, a different module for a different use case, untouched by this work) if Safety Shepherd is unreachable. 26 unit tests, all passing. **Verified against the live stack, not just unit-tested**: valid plan + real Shepherd up → `ESCALATE` (category `"docker"` is in Shepherd's `DANGEROUS` set, correctly needs an explicit grant — Shepherd's *existing*, unmodified policy engine handled this with zero Shepherd-side changes); Shepherd killed mid-request → `BLOCK`, `shepherd_available: false`; denied profile (`"prod"`) → `422`, confirmed via Shepherd's own logs that no `/evaluate` call was ever received. `execution.performed` is `false` in every case — no code path in the service can set it `true`. Whole 68-container fleet swept clean (zero unhealthy) before and after. Provisioned a real Governance Ledger key for `fleet-controller` via a **scoped single-row SQL insert**, not the full `scripts/seed_agent_api_keys.py` batch (which regenerates all 14 existing agents' keys — running it would have silently invalidated every other live agent's ledger-write key while their containers still held the old one; the other 14 rows in the DB were deliberately left untouched). Mission-director (the LLM planner) and all later phases (capability tokens, live execution) remain unbuilt, as designed — see the spec's Out of Scope section. | ✅ done |
| 3 | **Add resource limits** to all 12 new agents (`mem_limit: 256m`, `cpus: "0.25"`) | 🔴 Before launch |
| 4 | **Verify crew-orchestrator** has `restart: unless-stopped` + `/health` endpoint | 🔴 Before launch |
| 5 | **`docs/STATUS.md`'s "Agent Fleet — 25 Total" section is stale** — predates the 08-19/08-20 reconciliation, still shows the old wrong ports (e.g. `crew-orchestrator :8010` instead of the real `:8081`). Flagged with a banner in-place 2026-08-20, not rewritten — needs a real pass. | 🟡 doc debt |
| 6 | **✅ FIXED, 2026-08-21.** `ghost-agents-build.yml`'s build matrix `context:`/new `dockerfile:` paths were wrong for most/all of its 12 entries (e.g. `system-architect` pointed at `./agents/system-architect`, real dir is `agents/07-system-architect`). Re-derived every path from the real, live `docker-compose.agents.yml`/`agents-full.yml` service definitions; also fixed the file's `on.push.paths` trigger list (5 of 12 entries pointed at nonexistent directories too — the workflow would never even fire on real code changes) and the "agent directory exists" check (now checks the Dockerfile path, not just the context dir — several agents use `context: .`, which always exists and would've masked a missing Dockerfile). **Verified by parsing the real YAML `strategy.matrix.include` structure and confirming all 12 `context`/`dockerfile` pairs resolve to an on-disk file** — not by reading the source text. | ✅ fixed |
| 7 | **✅ FIXED, 2026-08-21.** `ghost-agents-build.yml`'s port-collision-check job (`port-check`) had a broken regex (`grep -oP '"\d+:\d+"'`, unanchored, never actually matched a real `"127.0.0.1:HOST:CONTAINER"` string) — likely never caught a real collision. Replaced with `.github/scripts/check_duplicate_ports.py` (shared with `health-check.yml`, see item #8) rather than patching the regex, because a regex-only fix immediately re-surfaces as new false positives (see #8's write-up) that bash/grep can't resolve without real YAML parsing. | ✅ fixed |
| 8 | **✅ FIXED, 2026-08-21.** `health-check.yml`'s `EXPECTED_PORTS`/duplicate-port checks were broken in three independent ways, found while actually running the fix (not just patching the reported symptom): (1) `host_port = str(p).split(':')[0].split('127.0.0.1:')[-1]` always yielded the literal string `'127.0.0.1'`, never a real port — every entry printed MISSING regardless of the dict. (2) Both checks only read `docker-compose.yml` (which has no `services:` of its own — it's a pure `include:` wrapper plain YAML never resolves) + `docker-compose.agents-full.yml`, silently never reading `docker-compose.agents.yml` — the file that actually owns 13 of the 26 fleet agents. (3) `EXPECTED_PORTS['8011']` for `frontend-specialist` was stale — its real, live port (confirmed against `CLAUDE.md`'s fleet table and the compose file itself) is `8012`. **A much bigger, separate finding surfaced while fixing all three**: the `python -c "<multi-line heredoc>"` pattern used in every affected step is invalid YAML — a literal block scalar's indentation floor is set by its first content line (`python -c "` at 10 spaces), and the un-indented Python code after it (column 0) drops below that floor, terminating the block scalar early. Confirmed with a minimal `pyyaml.safe_load` repro, not just inferred. Since `health-check.yml`'s *first* such block (`Validate docker-compose files`) predates and is unrelated to this item, and it also breaks this way, **the whole file was very likely never valid, executable GitHub Actions YAML** — `CLAUDE.md`'s "CI/CD Workflows Live" claim for `health-check.yml` needs retiring, not just this gate's logic. **Fix**: extracted all 4 embedded python blocks to real files (`.github/scripts/{validate_compose_yaml,check_duplicate_ports,check_expected_ports,check_fleet_controller_capabilities}.py`), called via plain single-line `run: python .github/scripts/X.py` — eliminates the heredoc-indentation trap entirely rather than re-indenting around it. `check_duplicate_ports.py` is shared with `ghost-agents-build.yml`'s port-check job (item #7) so the two gates can't drift. **Verified**: `yaml.safe_load()` on the full files now succeeds (both files), the parsed `steps[].run` values were pulled from the real parsed structure (not regex-scraped) and executed directly, and all 4 scripts pass clean against the live repo state (0 duplicates across 47 fleet-file port mappings using no profile filter, all 25 expected ports found). | ✅ fixed |
| 8a | **New, not fixed — found while building item #8's real (non-profile-filtered) duplicate-port scan.** `hypercode-ollama` (`docker-compose.core.yml`, no profile — always starts) and `hypercode-ollama-gpu` (`docker-compose.agents.yml`, `--profile gpu`) both bind host `127.0.0.1:11434`; `prometheus` (`docker-compose.observability.yml`, always starts) and `prometheus-cloud` (`docker-compose.grafana-cloud.yml`, `--profile grafana-cloud`) both bind `127.0.0.1:9090`. Neither has ever actually collided because nobody's passed `--profile gpu` or `--profile grafana-cloud` alongside the standard launch yet — but `hypercode-ollama-gpu` sets a network alias `hypercode-ollama` specifically so it can *swap in* for the base service, which only makes sense if the base is meant to be disabled first; there's currently no profile-based way to do that (the base has no profile gate at all). Needs Bro's call: gate the base `hypercode-ollama`/`prometheus` behind their own default-on profile so `--profile gpu`/`--profile grafana-cloud` can cleanly exclude them, or accept the two are simply never meant to be combined and document it. Deliberately excluded from `check_duplicate_ports.py`'s scope (agent-fleet files only, see that script's header) rather than silently allowlisted. | 🟢 found, not fixed |
| 9 | **✅ FULLY CLOSED, 2026-08-20 late evening (commit `84fa5a2d`).** `agents-full.yml` uniformly maps `HOST:8080`, but each agent's own Dockerfile/base template baked its own internal port independently, never reconciled against that. Audited all 24, fixed every port-mismatched one, then fixed the last 3 that couldn't even build. See `docs/AGENTS_FULL_PORT_AUDIT_2026-08-20.md` for full evidence. | ✅ 24/24 fine |
| 9a | **✅ Fine (21, was 4):** `crew-orchestrator`, `hyper-architect`, `test-agent`, `business-agent` were already fine. **17 more fixed this pass**, all now bake `AGENT_PORT=8080` (or `PORT=8080` for the 2 that use that name) matching compose's healthcheck: `project-strategist`, `coder-agent`, `frontend-specialist`, `backend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`, `security-engineer`, `system-architect`, `agent-x`, `throttle-agent`, `super-hyper-broski-agent`, `tips-tricks-writer` (also required removing a hardcoded `config.port = 8009` override in `agent.py` itself — the Dockerfile fix alone wouldn't have been enough), `hyper-split-agent`, `session-snapshot`, `goal-keeper`, `coderabbit-webhook` (also fixed a stale "started on port 8000" log message while in the file). **Verified**: `docker build` succeeded for a sample from each fix pattern (`system-architect`, `tips-tricks-writer`, `goal-keeper`, `hyper-split-agent` — one per group); a repo-wide grep for any remaining non-`8080` `AGENT_PORT=`/`PORT=`/`EXPOSE`/healthcheck/CMD-port reference across all 17 came back empty. | `agents/<name>/Dockerfile` (+ `agent.py` for tips-tricks-writer, `main.py` log line for coderabbit-webhook) |
| 9c | **✅ Fixed, 2026-08-20 late evening (commit `84fa5a2d`), verified by running all 3 standalone.** Was a build-context path bug, same class as the `hypercode-mcp-server` phantom fixed earlier tonight: `brain-agent` — `context: ./agents/brain` didn't exist as a directory; wrote a real implementation there. `hyper-observer`/`hyper-worker` — `agents-full.yml` expected `context: ./agents/hyper-agents, dockerfile: Dockerfile.observer`/`Dockerfile.worker`; the real Dockerfiles live one level deeper and `COPY` shared `src/agents/hyper_agents/` code, so compose's `context:` was repointed to repo root for both and `.dockerignore` fixed to stop excluding what the build needs. All 3 now bake `AGENT_PORT=8080`. **Verified this session**: `docker build` succeeded for all 3, then ran each standalone and hit `/health` — `brain-agent` → `{"status":"healthy","agent":"brain-agent"}` (200), `hyper-observer`/`hyper-worker` → `{"status":"ready",...}` (200 each). | `docker compose build` now succeeds for all 3; all pass a live `/health` check |

---

## 🪤 From the 2026-08-20 fleet-reconciliation + Docker health + dashboard playtest session

> Full write-up + evidence: `HperCore/NEXT_SESSION_HANDOVER_2026-08-20.md` and the published
> session-report artifact linked there. This table is the actionable subset — the fast version.

### Priority 1 — silently wrong, not just incomplete

| # | Task | Where |
|---|---|---|
| P1-1 | **High-Contrast theme toggle is a no-op** — selects itself active, changes nothing (pixel-identical to Default) | dashboard top-bar theme switcher |
| P1-2 | ✅ **Fixed 2026-08-20 evening** — turned out to be worse than "needs a rename": `agents-full.yml`'s `hypercode-mcp-server` block pointed at `./agents/hypercode-mcp-server`, which doesn't exist (no Dockerfile anywhere). It wasn't a distinct 25th agent to rename — it was a phantom duplicate of the already-live `:8823` service, and merging it silently swapped the real service's build context to the nonexistent path. **Deleted the block**, not renamed. `docker-push.yml`'s CI matrix entry was checked and is fine as-is (already points at the real `./services/hypercode-mcp-server` context). | `docker-compose.agents-full.yml` |

### Priority 2 — real, actionable, not urgent

| # | Task | Where |
|---|---|---|
| P2-1 | ✅ **Fixed for real, 2026-08-20 evening (part 5).** Old scaffold deleted (`agents/business/project-strategist/` — mislabeled project-strategist clone, `git rm -r`'d). Real `business-agent` now lives flattened at `agents/business/`: `agent.py` (`BusinessAgent` class — billing/subscription/revenue framing, read-only Stripe balance+recent-charges snapshot via `STRIPE_API_KEY` as LLM grounding context, never writes/mutates payment state), `base_agent.py` (copied from the newer, cleaner `agents/09-tips-tricks-writer` template, not the older buggy one the scaffold had), `Dockerfile` (hardened multi-stage, modeled on `agents/07-system-architect`, `AGENT_PORT=8080` baked in to match compose's hardcoded `:8080` healthcheck — the old scaffold's `EXPOSE 8019` never matched compose's `:8020→:8080` mapping or its own `AGENT_PORT` default, a container-port bug independent of the mislabeling), `config.json`, `HYPER-AGENT-BIBLE.md`. **Verified, not just written**: `docker build` succeeded, `docker run` + `curl /health` returned `{"status":"healthy","agent":"business-agent"}` (200), `/execute` with a real request returned a correct response shape, auth middleware correctly 401'd an unauthenticated request. `docker-push.yml`'s CI matrix context fixed from the nonexistent `./agents/business-agent` to the real `./agents/business`. | `agents/business/` |
| P2-2 | ✅ **All 5 fixed, 2026-08-20 evening**, verified via `docker compose config` (not grep): `system-architect` :8008→:8010 (was colliding with live `healer-agent`), `hyper-split-agent` :8096→:8013 (was colliding with live `safety-shepherd`), `session-snapshot` :8097→:8017 (was colliding with live `evolve-relay`, `--profile pets`), `tips-tricks-writer` :8009→:8018 (was colliding with live `chroma`), `test-agent` :8100→:8019 (was colliding with live `hyper-brain`, `--profile brain`) — last two found this session, not in the original P1/P2 list. Also fixed the same pass: the launch command's missing `--profile agents` flag (not a port issue — see item #0/#1 above, now documented as required). | `docker-compose.agents-full.yml` |
| P2-3 | **`/agents` dashboard page shows 3 agents; real fleet is 42** — it reads the BROski XP table, not the live container list. `/control` (Mission Control) gets it right, one click away. | dashboard `/agents` |
| P2-4 | **`/health` dashboard page's ghost-agent ports are stale** — Test Agent and Agent X both still show `:8080` (pre-reconciliation number; real ports are `:8100` and `:8083`/`:8084`). Hardcoded in dashboard source, doesn't read compose. | dashboard `/health` |
| P2-5 | **Hyperfocus Universe's GitHub sync is broken** — every one of 84 worlds shows "Updated 1 month ago" incl. repos pushed today. The site's own quest log names the cause: Vercel's GitHub App was never granted repo access. | `Hyperfocus-Universe-The-Living-Hub` Vercel project settings |
| P2-6 | **Hyperfocus Universe's quest-log filename check is wrong** — looks for `WHATS-DONE.md` (hyphenated); every real repo uses `WHATS_DONE.md` (underscored). Can never detect a signal that already exists. | `Hyperfocus-Universe-The-Living-Hub` quest-detection logic |

### Priority 3 — worth doing, low stakes

| # | Task | Where |
|---|---|---|
| P3-1 | Point Docker Zone's one-click "Send" launch commands at `hyperlaunch.ps1` instead of a bare `docker compose -f ... up --watch` that skips the 3 required files | dashboard `/docker-zone` |
| P3-2 | Stop treating `/api/ops/dlq` 400s as an error-rate signal — DLQ is deliberately superuser-gated; the home screen's "Error Rate 28.57%" is just this gate polling forever (same class as the existing perma-red note below) | dashboard Hyper Station metrics |
| P3-3 | Add `hyper-auto-assistant` (port `:8016`) to the roster docs — Mission Control already tracks it, it's agent 26, not a bug | `AGENT-START.md` |
| P3-4 | Make the Universe 3D view's planets actually clickable — "pick a world to descend into it" doesn't currently open anything (tried 3 large centered planets, no panel, no console error) | `Hyperfocus-Universe-The-Living-Hub` 3D view |
| P3-5 | Grafana embed has no SSO — real login wall every visit, no session handoff from the dashboard | dashboard `/grafana` |

---

## 🟡 This Week

| # | Task | Priority |
|---|---|---|
| 5 | **Push to GHCR** — tag + push all 12 new images to `ghcr.io/welshdog/` | 🟡 This week |
| 6 | **GitHub Actions CI/CD** — auto-build on push to `main` | 🟡 This week |
| 7 | **BROskiPets Web3 E2E** — test mint on Base Sepolia testnet (MetaMask = human gate) | 🟡 This week |
| 8 | **Fix GitHub Actions billing lock** — github.com/settings/billing (human gate) | 🟡 This week |
| 9 | **`/welcome` auth-gate decision** — make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |

---

## 🟢 Background / Non-Blocking

| # | Task | Priority |
|---|---|---|
| 10 | **Course AI Agents 2.0 (P2-4, M11+)** — final piece of AGENT-START roadmap in `Hyper-Vibe-Coding-Course` | 🟢 Next session |
| 11 | **Discord Bot Tier 2** — Pets, XP Leaderboard, Morning Briefing, Health Alerts | 🟢 Background |
| 12 | **HyperLabs human gates** — Vercel Speed Insights CWV · `/pets` wallet smoke · post-login reconcile | 🟢 |
| 13 | **Stripe LIVE mode** — add LIVE price IDs + endpoint + pick secret by `event.livemode` | 🟢 After Companies House |
| 14 | **Companies House reg (£50, SIC 62012)** — human gate → Stripe LIVE → first real £ | 🟢 Human gate |
| 15 | **T&Cs + privacy + refund pages** — code-ready when Companies House reg lands | 🟢 |
| 16 | **Shop Fulfillment v2** — deploy + E2E pending | 🟢 |

---

## ⏰ Reminders & Expiry Dates

| Item | Date | Action |
|---|---|---|
| Service JWT (`DASHBOARD_SERVICE_JWT`) | Expires **2027-07-13** | Re-mint via `create_access_token(1, timedelta(days=365))` — symptom = 401s |
| Metrics error-rate cosmetics | — | confirmed 2026-08-20: it's `/api/ops/dlq` 400s from the deliberate superuser gate, not real errors — see P3-2 above |

---

## ✅ Completed — 2026-08-20 Evening Session, part 2 (fleet dedupe decision)

Presented Bro 4 options for the 14-name overlap (item #0): retire agents-full.yml's
duplicates in favor of agents.yml, rename agents-full.yml's versions, give
agents-full.yml distinct service names, or stop composing the two files together.
**Decision: stop composing them together** — leaves both files' content intact
(nothing deleted), kills the silent-merge risk immediately, fully reversible. The
permanent fix (which side ultimately owns these 14 agents) is still open — this
only stops the accidental hybrid-merge hazard. Documented in `CLAUDE.md`'s launch
command, `agents-full.yml`'s own header, and item #0 above.

Also corrected `business-agent`'s status while looking at the same file: a
Dockerfile *does* exist (`agents/business/project-strategist/Dockerfile`, one
directory level deeper than compose's `context:` looks) — but its own
`config/business-agent.json` identifies itself as `"Project Strategist"`, and it
exposes `:8019` not compose's `:8020`. Looks like a project-strategist directory
cloned as a business-agent starting scaffold and never customized. Did NOT wire
compose to point at it — that would silently deploy mislabeled code under the
business-agent name. P2-1 still needs a human decision, just a more precise one now.
*(Update: real business-agent code shipped later the same evening — see "part 5" below.)*

## ✅ Completed — 2026-08-20 Evening Session, part 3 (tips-tricks-writer vs chroma)

| Done | Where |
|---|---|
| `tips-tricks-writer` moved :8009→:8018 (was colliding with live `chroma`) — verified via `docker compose config`, confirmed :8009 now resolves to `chroma` only | `docker-compose.agents-full.yml` |
| Synced: `fleet-roster-check.sh` (re-run, clean), `health-check.yml`'s `EXPECTED_PORTS`, `CLAUDE.md`'s fleet table + launch-command warning, `NEXT_TASKS.md` | see files above |

## ✅ Completed — 2026-08-20 Evening Session, part 4 (test-agent vs hyper-brain)

| Done | Where |
|---|---|
| `test-agent` moved :8100→:8019 (was colliding with live `hyper-brain`, `--profile brain`) — verified via `docker compose config`, confirmed :8100 now resolves to `hyper-brain` only | `docker-compose.agents-full.yml` |
| **Correction to part 3's note above:** re-checked whether `test-agent` was really one of item #0's 14 same-name-merge cases before fixing it — it wasn't. That claim came from an earlier, broader `comm` check that accidentally included `docker-compose.on-demand.yml` (not part of the base `include:` chain). Re-ran the check restricted to the true base-include file set: `test-agent` isn't there. It was a plain port collision the whole time, fixed the same way as `tips-tricks-writer`. | evidence: `comm -12` re-run against the correct file set |
| Synced: `fleet-roster-check.sh` (emptied the now-resolved `COLLISIONS` array, re-run clean), `health-check.yml`'s `EXPECTED_PORTS`, `CLAUDE.md`'s fleet table + launch-command warning + port-validation note, `NEXT_TASKS.md` | see files above |

**All real port-vs-differently-named-service collisions in `agents-full.yml` are now fixed.** Only item #0 (the 14-name same-name-merge architecture decision) remained open — see part 5 below for `business-agent`.

## ✅ Completed — 2026-08-20 Evening Session, part 5 (business-agent built for real)

| Done | Where |
|---|---|
| Old mislabeled scaffold deleted (`git rm -r`) — was a stray clone of `08-project-strategist`'s code, config, and Bible, never customized for business-agent | `agents/business/project-strategist/` |
| Real `business-agent` written: `agent.py` (billing/subscription/revenue framing, read-only Stripe balance+recent-charges snapshot as LLM grounding, never writes/mutates payment state — that stays in `agents/stripe-mcp`), `base_agent.py` (copied from the newer `agents/09-tips-tricks-writer` template, not the older buggy one the scaffold had), `Dockerfile`, `config.json`, `HYPER-AGENT-BIBLE.md` | `agents/business/` (flattened to match compose's `context:` — no more extra nesting) |
| Fixed a second, independent bug found while building it: the old scaffold's `EXPOSE 8019` never matched compose's `:8020→:8080` mapping *or* its own base template's `AGENT_PORT` default — three disagreeing port numbers. New Dockerfile bakes `AGENT_PORT=8080` to match compose's hardcoded `curl http://localhost:8080/health` healthcheck. | `agents/business/Dockerfile` |
| **Verified, not just written**: `docker build -t hypercode-business-agent:test ./agents/business` succeeded; `docker run` + `curl /health` returned `{"status":"healthy","agent":"business-agent"}` (200) and `docker ps` showed `(healthy)`; `POST /execute` with a real payload returned the correct response shape (LLM call itself failed gracefully — no backend LLM in the standalone test, expected); unauthenticated `POST /execute` correctly 401'd. Test container + image removed after. | verified via standalone `docker run`, not composed |
| `docker-push.yml`'s CI matrix context fixed: `./agents/business-agent` (never existed) → `./agents/business` (real) | `.github/workflows/docker-push.yml` |
| Synced: `fleet-roster-check.sh` (`business-agent` no longer `BLOCKED`, 0 blocked now, script exits 0), `CLAUDE.md`'s fleet table + total counts, `NEXT_TASKS.md` P2-1 | see files above |

**business-agent is no longer a blocker for anything.** The only thing standing between the current state and a real fleet launch is item #0 (the 14-name architecture decision) — everything else in `NEXT_TASKS.md`'s original P1/P2 launch-blocker list is now closed.

## ✅ Completed — 2026-08-20 Evening Session (agents-full.yml collision fixes + architecture audit)

| Done | Where |
|---|---|
| Phantom `hypercode-mcp-server` ghost block deleted (nonexistent build context, name+port collision with the real live service) | `docker-compose.agents-full.yml` |
| 3 real port collisions fixed + verified via `docker compose config`: `system-architect` :8008→:8010, `hyper-split-agent` :8096→:8013, `session-snapshot` :8097→:8017 | `docker-compose.agents-full.yml` |
| `--profile agents` documented as required in the fleet launch command — without it `crew-orchestrator` silently drops from the merge and `docker compose config` hard-fails | `CLAUDE.md`, `docker-compose.agents-full.yml` header |
| `fleet-roster-check.sh` roster/collision tables updated to match (24-entry roster, `hypercode-mcp-server` no longer listed as a distinct ghost) — script re-run and confirmed exit 0 | `scripts/fleet-roster-check.sh` |
| `docs/STATUS.md`'s stale "Agent Fleet — 25 Total" section flagged in-place (wrong ports, predates reconciliation) — not rewritten, needs its own pass | `docs/STATUS.md` |
| **New finding, not previously documented:** 14 of ~24 agent names in `agents-full.yml` are also defined in `docker-compose.agents.yml` with different build contexts/ports/profiles — same-name merge across compose files, unaudited. Logged as item #0 above. | evidence via `comm` diff, see item #0 |
| **New collision found, not in the original P2-2 list:** `tips-tricks-writer` (:8009) vs live `chroma` — ✅ fixed later the same evening, see "part 3" section above | `docker-compose.agents-full.yml` |

## ✅ Completed — 2026-08-20 Session (fleet reconciliation + health + playtest)

| Done | Commit |
|---|---|
| Root doc chain repaired (`DASHBOARD_STATUS`/`NEXT_SESSION_HANDOVER` `LATEST` pointers, both were stale/broken) | workspace root, not git |
| 4 conflicting "25-agent fleet" rosters (`AGENT-START.md`, `CLAUDE.md`, `docker-push.yml`, + original) reconciled to one | `0ad90a14` |
| 5 of 6 broken `docker-push.yml` ghost-agent CI build paths fixed | `0ad90a14` |
| `scripts/fleet-roster-check.sh` shipped — narrow live/built/blocked check for the canonical 25-agent roster | `fb696851` |
| `health-check.sh` fixed — was dying after line 1 on every run (`set -e` + `((PASS++))` bug) | `e1d1456f` |
| Real compose validation failure fixed — `prometheus` defined twice across `docker-compose.observability.yml` + `docker-compose.grafana-cloud.yml` | `e1d1456f` |
| `agent-hyperfocus-copilot` unhealthy → healthy (stale volume mount, container recreated) | runtime, no diff |
| `project-strategist` restarted (had exited 16h earlier, never came back) | runtime, no diff |
| `github-sync-brain` healthcheck fixed for real (`pgrep` → `/proc/1/comm`) | `f87370e1` |
| 7 trivial dangling volumes removed (~80KB); ~2GB of real observability/Supabase data left untouched | docker, no diff |
| Full stack confirmed healthy: 51/51 running, 0 stopped, 0 unhealthy | verified twice |
| Dashboard, Constellation, Hyperfocus Universe playtested live — 13 findings logged above | see P1-P3 tables |

## ✅ Completed — August 2026 Session

| Done | Date |
|---|---|
| All 12 ghost agents identified + Dockerfiles created | 2026-08-19 |
| `BUILD_ALL_AGENTS_GUIDE.md` + `QUICK_START_12_AGENTS.md` + `AGENTS_BUILD_STATUS.md` + `AGENT_BUILD_SESSION_SUMMARY.md` committed | 2026-08-19 |
| `build-all-agents.ps1` + `start-all-agents.sh` automation scripts committed | 2026-08-19 |
| Commits: `296e3a36`, `22089803`, `61bc5ca5` all on `origin/main` | 2026-08-19 |

---

## ✅ Completed — July 2026 Sessions

| Done | Date |
|---|---|
| Crew-orchestrator safety intercept · Mission Control `/control` · HS-P2c governance-ledger write · PITCH-KIT.md | 2026-07-12 |
| ALL 8 PLAYTEST FIXES SHIPPED + VERIFIED LIVE (9/9 smoke, zero 4xx/5xx) | 2026-07-13 |
| HyperStudio P1–P4 all phases LIVE | 2026-07-13 |
| LinkedIn headline + GitHub pins | 2026-07-12 |

---

## 🏗️ HyperStudio Phases

| # | Task | Status |
|---|---|---|
| HS-P1 | Phase 1 write path | ✅ Done 2026-07-10 (PR #315) |
| HS-P2a | Interactive ESCALATE approval | ✅ Done 2026-07-11 (PR #316) |
| HS-P2b | Specialist agents roster | ✅ Live |
| HS-P2c | Governance-ledger write | ✅ LIVE 2026-07-13 |
| HS-P3 | Crew-orchestrator → Shepherd intercept | ✅ LIVE 2026-07-12 |
| HS-P4 | Mission Control `/control` | ✅ LIVE 2026-07-13 |

---

## AGENT-START Roadmap

| Task | Status |
|---|---|
| P0-1 HyperFlow | ✅ 2026-06-19 |
| P0-2 Safety Shepherd | ✅ 2026-06-19 |
| P0-3 Mission Graph Panel | ✅ 2026-06-19 |
| P1-1 BROski Identity Agent | ✅ 2026-06-19 |
| P1-2 Governance Ledger | ✅ 2026-06-19 |
| P1-3 Skills to HYPER-SILLs | ✅ 2026-06-19 |
| P1-4 Specialist BIBLEs | ✅ 2026-06-19 |
| P2-1 Evo Harness | ✅ 2026-06-20 |
| P2-2 Brain Constellation L20 | ✅ 2026-06-20 |
| P2-3 Brain Levels 18+19 | ✅ 2026-06-20 |
| **P2-4 Course AI Agents 2.0 (M11+)** | ⬜ **THE FINAL PIECE** |
