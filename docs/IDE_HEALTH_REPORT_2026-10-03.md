# 🩺 HyperCode Dashboard IDE — Health Check & Status Report

> **Target:** `http://127.0.0.1:8088/ide` (and every page behind its sidebar) · **When:** 2026-10-03 ~13:30–14:40 UTC (read-only: nothing was changed, restarted or paused) ·
> **How:** API probes of every page + every safe route, response-body checks, dashboard/core container logs, and a real Chrome walkthrough of each panel (console + network).
> Memory stayed GREEN throughout (host 730 MB free, compression 1.1 GB, WSL 1.5 GB).

## 🟢 OVERALL: HEALTHY, with a short list of real defects (none stops the IDE working)

| Area | Status | Evidence |
|---|---|---|
| Dashboard container | ✅ | healthy, 0 restarts, 43 MiB / 512 MiB, **0 errors in the last hour's log** |
| Pages (10) | ✅ | `/ide /agents /control /docker-zone /flows /grafana /health /mcp /mission /sensory` all **200**, 0.01–0.17 s |
| API routes (21 GET) | ✅ | 19 × 200; `/api/skills` + `/api/planning` = 405 **by design** (POST-only, confirmed in source) |
| `/ide` page load (browser) | ✅ | 18 requests, all 200 (HTML, JS, CSS, 6 fonts, crew calls); **no console errors** |
| Live data | ✅ | SSE `/api/events` streams; "Live logs connected"; metrics refresh; Morning Card, Panic, crew run all respond |
| Core / Orchestrator / Healer | ✅ | Health page: all HEALTHY, fresh timestamps; healer: redis ✓ docker ✓ event bus ✓ circuit breaker off |
| MCP server | ✅ | `ok` over SSE |
| DLQ | ✅ | empty (size 0) |
| Studio (coder-studio) | ✅ | `ok`, 0/200 sessions |

## 🟡 ISSUES (ranked)

1. **BROski Pulse shows wrong numbers (Total XP 0, agents 0)** — two small bugs in `agents/dashboard/app/api/pulse/route.ts` (pre-existing, not from today): (a) core's `/api/v1/broski/pulse` returns `coins`/`xp`, but the route reads `broski_coins`/`total_xp` → always 0 (real: **25 coins, 6,705 XP, level 7**);
   (b) the route sends **no credential** to `/api/v1/orchestrator/agents`, which returns **401**, so it silently falls back to 0 agents (with the dashboard's service JWT core returns **11 agents**). It also fails *silently* to zeros, which hides the problem. Fix = map the field names + use `serviceAuthHeader()` + stop swallowing non-OK.
2. **Safety Feed: "20 awaiting approval" are real ESCALATEs** — the orchestrator's dispatch check asks Shepherd about tools `crew_build` (coder-agent, 14×) and `crew_verify` (qa-engineer, 6×); `agents/safety-shepherd/capabilities.json` does not list them (`coder_agent` may use only file_read/file_write/git; `qa_engineer` only file_read/http_external) → "tool … not granted".
   **The crew only works because core and the orchestrator run `SAFETY_SHEPHERD_MODE=monitor` (record, don't block). If anyone switches to `enforce`, every crew build/verify would stall waiting for a human.** *(This corrects my earlier note that Shepherd "answers ALLOW for crew build/verify/publish": that was true only for the flow runner's generic check.)* Decide: grant those tools, or keep monitor mode knowingly.
3. **One stale parked crew run** — `01908424-8c21…` (crew, created 11:38 UTC) sits at the plan gate; it is the "1 run is waiting on you" in the Morning Card and the amber light. A leftover from a proof attempt; cancel it (run totals: 17 completed, 9 failed, 7 cancelled, 1 parked).
4. **Services panel says CRITICAL / Mission Control "10 down"** — fleet roster of 42: **17 up, 15 not_deployed, 10 missing**. Mostly intentional (agents stopped to save RAM; 18 "ghost agents" on the Health page). Plus **9 leftover auto-named stopped containers** (`sweet_bose`, `frosty_benz`, `quirky_bose`, `eager_engelbart`, `exciting_solomon`, `frosty_einstein`, `goofy_hoover`, `priceless_hellman`, `xenodochial_jackson`) from old `docker run` sessions that show as DOWN and add noise (they hold no RAM).
5. **Agents panel lists only 3 agents** (celery-worker, healer-agent, hypercode-core) while 17 are live: it shows registry heartbeats only (the route's own comment says it avoids the 401'd endpoint). Misleading, not broken.
6. **Grafana panel: "127.0.0.1 refused to connect"** — expected: the observability stack (Grafana :3001) is stopped to save RAM. The panel chrome still renders.
7. **Orchestrator health cache is empty** — `/api/orchestrator` returns "health cache empty — service alive" (its monitor loop isn't filling the Redis cache). Minor.
8. **Two slow endpoints:** `/api/metrics` 2.7 s and `/api/mcp/health` 3.7 s (the former was ~9 s earlier today). Not failing; worth watching.

## 🔵 MINOR / FYI

- **Docker Zone page is static** (hard-coded "LIVE" hot-reload badge); it shows a Docker Scout CVE baseline of **24 critical / 224 high (10 images) dated 2026-09-07** — 26 days old.
- Core logged 3 × `404 POST /api/v1/economy/award-from-course` in 30 min: not the dashboard (no caller in its source); most likely the local commit-XP hook. Core's `/api/metrics` error rate read 4.35 %.
- `/api/tasks` holds one old queued manual task from 2026-07-14 ("Run full system diagnostic…").
- **Unexplained clean dashboard restart** at 12:50:23 UTC (exit 0, RestartCount 0; not the healer, no Docker events found).
- The browser window is narrow (can't be resized from here), so the layout I saw was the compact one.

## ❌ NOT TESTED

Running a real task in Studio (agent stream / diff & review), the Plan Generator, Panic with a *running* crew run, any POST proxy (execute, DLQ replay), keyboard/screen-reader accessibility, the wide-screen layout, and behaviour after a Docker Desktop restart.

## ✅ FOLLOW-UP — the four suggested fixes were done (15:10 UTC), with two corrected diagnoses

| # | Fix | Result |
|---|---|---|
| 1 | Cancel the stale parked run `01908424-8c21…` | Cancelled through the operator API (HTTP 200); runs: 17 completed / 9 failed / 8 cancelled / **0 parked**. **Morning Card is now green** ("Fleet: green (1.8 GB free)", no "waiting on you"). |
| 2 | Pulse | `/api/pulse` now returns **25 coins, 6,705 XP, 11 agents**, no `degraded`. **Correction:** the visible panel never used that route — it summed the agents' own XP (0) and ignored the user's `xp` that `/api/broski` returns; the panel now shows the real XP (fallback: agent sum). 12 new tests (5 red on the old code). `healthy_agents` is honestly 0/11: core's 11 are a static roster, all `idle`, not a liveness signal. Commit `63f5edd2`. |
| 3 | Shepherd grants | **Root cause was bigger than the missing grant:** `policy._agent_caps` is an exact-key lookup and the manifest's per-agent entries are *underscored* (`coder_agent`, `qa_engineer`) while the orchestrator sends *hyphenated* names (`coder-agent` ×21, `qa-engineer` ×9 in the feed). Those agents never matched their own entries and ran on the **`*` wildcard** (tools: `file_read` only). Fix (data-only, least privilege): two hyphenated entries = the wildcard's current rights **+ exactly one crew tool each** (`coder-agent`: `crew_build`, `qa-engineer`: `crew_verify`); the underscored entries are untouched. Safety-shepherd rebuilt + recreated; **live check: 7/7 decisions as designed** (both crew tools ALLOW; builder can't verify, verifier can't build; file_write/docker still ESCALATE; underscored names still ESCALATE). 41 policy tests (3 red without the entries; a battery test proves the new entries equal the wildcard apart from their crew tool). Commit `f83c8321`. |
| 4 | Remove 9 stray containers | Inspected first (all exited, 0 mounts, none running, no data), then `docker rm` of exactly those 9 names (no `-f`, no `-v`): 21 → 12 stopped (the 12 are the obs stack, by design); 36 running unchanged. |

**Resolved 15:20 UTC (`55aea70a`, approved by Lyndz):** `_agent_caps` now resolves exact name → hyphen/underscore variant → `*`, so **backend-specialist, frontend-specialist, devops-engineer and database-architect now get their real grants** (e.g. backend-specialist may write `backend/**`, devops-engineer may use docker, frontend-specialist may reach github.com / registry.npmjs.org). An exact match always wins (the crew entries keep precedence); hard-blocked paths and system paths stay BLOCK for all four. **`coder-studio` was deliberately excluded**: its `**` path grant relies on Studio's client-side worktree boundary (it sends the name `coder_studio`), so the entry is flagged `"exact_name_only": true` and the hyphenated spelling stays on the wildcard. Simulated before the change (15 decision cells moved), 124 shepherd tests pass (reverting the lookup breaks 16, removing the guard breaks 1), and **live-verified after the redeploy: 0 mismatches across 4 agents × 6 requests, coder-studio / unknown-agent behaviour unchanged, the 7 crew decisions unchanged.** Still true: core + orchestrator remain in `monitor` mode.
Process notes: the deploy was gated on the guard; it correctly **stopped at the first gate** (AMBER) and only proceeded after the browser closed and I stopped my own optional `fcc-proxy` (restarted afterwards, healthy). My first policy-test append silently went to the wrong directory (a stray root `test_policy.py`, deleted) so my first "mutation check" proved nothing — I caught it because the check passed when it should have failed, and redid it.

## ▶️ SUGGESTED FIXES (small → bigger) — original list, now done (see above); remaining: 5. restart Grafana when RAM allows, 6. refresh the Scout baseline, 7. decide on `_agent_caps` normalisation

1. Cancel the stale run `01908424…` (clears the amber light). 2. Fix `pulse/route.ts` (2 field names + service JWT). 3. `docker rm` the 9 stray stopped containers (your call). 4. Decide Shepherd: grant `crew_build`/`crew_verify` or keep monitor mode on purpose. 5. Restart Grafana when RAM allows. 6. Refresh the Scout baseline.
