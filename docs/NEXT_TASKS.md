# 🎯 Active Next Tasks
> Update this every session. Completed items → `WHATS_DONE.md`.
> For sacred rules + architecture → `CLAUDE.md`
> Last updated: **August 20, 2026 (evening pass)**

---

## 🔥 Immediate — Do These First

> ⚠️ **"Launch 25-agent fleet" below is NOT ready — and it's a much bigger job than "fix 3 ports".**
> A second 2026-08-20 pass verified the actual merge with `docker compose config` (not just grep)
> and found the real picture was worse than the morning session's port-clash list: one phantom
> agent, a missing required flag that broke the documented launch command outright, and a
> same-name-merge problem across 14 agent definitions (item #0 — mitigated, not resolved). A
> **third, independent pass the same night audited every remaining agent's container-internal
> port** (item #9) and found `agents-full.yml`'s uniform `HOST:8080` mapping doesn't match what
> 20 of 24 agents' own Dockerfiles actually bind to — 17 would be unreachable via their host
> port even though they'd build and pass their own healthcheck, and 3 can't even build. **Fixing
> item #0 alone would not make this file launchable** — item #9 is a separate, additional
> blocker layered underneath it. Full detail in items #0 and #9 below.

| # | Task | Priority |
|---|---|---|
| 0 | **DECIDED 2026-08-20 evening (Bro's call): don't compose `docker-compose.agents-full.yml` together with the base stack at all**, until the underlying overlap is fixed for real. Background: 14 of ~24 agent names in `agents-full.yml` are *also* defined in `docker-compose.agents.yml` (or other base-included files) with **different build contexts, ports, or profiles**. Compose merges same-named services across `-f` files instead of erroring — the later file's `build.context`/`image` wins silently, list fields like `ports` get unioned. Proven on two: `hypercode-mcp-server`'s ghost definition silently swapped the real service's build context to a nonexistent path, and `hyper-architect` has a second definition in `agents.yml` (`profiles:["hyper"]`, different Dockerfile path) that vanishes from the merge under `--profile agents`. 9 of the 14 overlapping names are confirmed live right now via the base stack (`docker ps` + container labels), not via `agents-full.yml`, which has never actually been composed up. **The permanent fix (rename one side / retire duplicates / distinct service names) is still undecided** — this entry only closes the "don't silently merge them" risk, documented in `CLAUDE.md`'s launch command and `agents-full.yml`'s own header. Evidence: `comm -12 <(grep names from agents-full.yml) <(grep names from agents.yml+core+observability+brain+bropets+obsidian-sync+grafana-cloud)` → 14 real agent names + 3 shared network names. | 🟡 mitigated, permanent fix still open |
| 1 | ~~Verify no port clashes~~ ✅ Done 2026-08-20 morning pass — found 3; ✅ **all fixed** across the full 2026-08-20 evening (see Completed tables). Final tally: `system-architect`, `hyper-split-agent`, `session-snapshot`, `tips-tricks-writer`, `test-agent` all moved off colliding ports. The launch command's missing `--profile agents` flag is now documented as required. **Correction:** an earlier pass in this same session mis-filed `test-agent` as one of the item-#0 same-name-merge cases — re-checked directly against the true base-include file set and it was never in that list, just a plain port collision (same class as `tips-tricks-writer`). Fixed accordingly, no architecture decision needed for it. | ✅ all fixed |
| 2 | **Launch 25-agent fleet** — item #9's 17 port-mismatched agents are now fixed (see item #9 below). Still blocked on: item #0's permanent fix (rename/retire/distinct-names decision, currently means "don't even try") AND the 3 remaining item #9c agents that can't build (`brain-agent`, `hyper-observer`, `hyper-worker`) — not fixed, need a path decision first. | 🔴 blocked, not ready |
| 3 | **Add resource limits** to all 12 new agents (`mem_limit: 256m`, `cpus: "0.25"`) | 🔴 Before launch |
| 4 | **Verify crew-orchestrator** has `restart: unless-stopped` + `/health` endpoint | 🔴 Before launch |
| 5 | **`docs/STATUS.md`'s "Agent Fleet — 25 Total" section is stale** — predates the 08-19/08-20 reconciliation, still shows the old wrong ports (e.g. `crew-orchestrator :8010` instead of the real `:8081`). Flagged with a banner in-place 2026-08-20, not rewritten — needs a real pass. | 🟡 doc debt |
| 6 | **`.github/workflows/ghost-agents-build.yml`'s build matrix `context:` paths are wrong for most/all of its 12 entries** — e.g. `system-architect: context: ./agents/system-architect` but the real directory is `agents/07-system-architect`; `tips-tricks-writer`, `hyper-architect`, `hyper-observer`, `hyper-worker` all point at directories that don't exist either (verified with `ls`, real paths differ — `hyper-architect`'s real context per `agents-full.yml` is `./agents/architect`). This file's builds would fail for most agents if triggered. Did NOT fix — separate, larger problem from tonight's port-collision work, needs its own pass reconciling all 12 context paths against what actually exists on disk. `health-check.yml`'s `EXPECTED_PORTS` dict *was* synced to tonight's 3 port changes (it's a simple, working YAML-port-diff check, unlike this file). | 🟡 CI debt, separate from #0 |
| 7 | **`ghost-agents-build.yml`'s own port-collision-check job (`port-check`) has a broken regex** — `grep -oP '"\d+:\d+"'` isn't anchored to the start of the port string, so on `"127.0.0.1:8008:8080"` it can match a garbage substring like `"1:8008"` instead of the real host/container ports. This gate has likely never reliably caught a real collision — possibly why the 08-19 session's "3 collisions fixed" claims needed a second, deeper pass tonight to find the real ones. Not fixed — needs a proper regex (`published:` field from `docker compose config`, not raw grep on the source YAML). | 🟡 CI debt |
| 8 | **`health-check.yml`'s `EXPECTED_PORTS` gate has always been broken, pre-existing, not caused by tonight's dict edit**: `host_port = str(p).split(':')[0].split('127.0.0.1:')[-1]` on a port string like `"127.0.0.1:8010:8080"` yields the literal string `'127.0.0.1'`, never a real port number — verified by running the exact line in isolation. `found_ports` therefore never matches any `EXPECTED_PORTS` key and this gate would print every entry as MISSING and fail, regardless of what the dict says or whether the underlying compose file is correct. Tonight's dict edit (syncing the 3 moved ports + dropping `hypercode-mcp-server`) keeps the dict *accurate*, but doesn't fix the parser — that's a separate, pre-existing bug. Needs `p.split(':')[-2]` (or equivalent) to actually extract the host port. | 🟡 CI debt, pre-existing |
| 9 | **✅ AUDIT COMPLETE + 17 OF 20 FIXED, 2026-08-20 late evening.** `agents-full.yml` uniformly maps `HOST:8080`, but each agent's own Dockerfile/base template baked its own internal port independently, never reconciled against that. Audited all 24, then fixed every port-mismatched one (not just audited this time). See `docs/AGENTS_FULL_PORT_AUDIT_2026-08-20.md` for full evidence (now updated with fix status). | ✅ 21/24 fine now, 3 still can't build |
| 9a | **✅ Fine (21, was 4):** `crew-orchestrator`, `hyper-architect`, `test-agent`, `business-agent` were already fine. **17 more fixed this pass**, all now bake `AGENT_PORT=8080` (or `PORT=8080` for the 2 that use that name) matching compose's healthcheck: `project-strategist`, `coder-agent`, `frontend-specialist`, `backend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`, `security-engineer`, `system-architect`, `agent-x`, `throttle-agent`, `super-hyper-broski-agent`, `tips-tricks-writer` (also required removing a hardcoded `config.port = 8009` override in `agent.py` itself — the Dockerfile fix alone wouldn't have been enough), `hyper-split-agent`, `session-snapshot`, `goal-keeper`, `coderabbit-webhook` (also fixed a stale "started on port 8000" log message while in the file). **Verified**: `docker build` succeeded for a sample from each fix pattern (`system-architect`, `tips-tricks-writer`, `goal-keeper`, `hyper-split-agent` — one per group); a repo-wide grep for any remaining non-`8080` `AGENT_PORT=`/`PORT=`/`EXPOSE`/healthcheck/CMD-port reference across all 17 came back empty. | `agents/<name>/Dockerfile` (+ `agent.py` for tips-tricks-writer, `main.py` log line for coderabbit-webhook) |
| 9c | **🔴 Can't even build (3), NOT fixed this pass — a build-context path bug, same class as the `hypercode-mcp-server` phantom fixed earlier tonight, needs a path decision not a port bake:** `brain-agent` — `context: ./agents/brain` doesn't exist as a directory at all. `hyper-observer`/`hyper-worker` — `agents-full.yml` expects `context: ./agents/hyper-agents, dockerfile: Dockerfile.observer`/`Dockerfile.worker` at the top of that directory; the real Dockerfiles exist one level deeper, misplaced at `agents/hyper-agents/observer/Dockerfile` and `agents/hyper-agents/worker/Dockerfile` (their `AGENT_PORT=8092`/`8093` bakes were also still wrong — would need the same fix once/if the path issue is resolved). | `docker compose build` fails outright for these 3 |

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
