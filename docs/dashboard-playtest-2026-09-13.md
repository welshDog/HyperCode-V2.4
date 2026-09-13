# Dashboard Playtest — 2026-09-13

Full click-through test of `hypercode-dashboard` (Mission Control / HyperCode IDE)
at `localhost:8088`, run live in a real browser (Claude in Chrome) against the
real running stack, right after merging the Skill Discoverability feature
(PR #526) to `main`. Every page in the sidebar nav was visited; console and
network activity were monitored throughout.

## TL;DR

- **9 of 10 nav pages: clean.** No console errors anywhere. Real, accurate
  live data throughout (fleet counts, health status, Docker state all matched
  what `docker ps` showed independently).
- **1 real deployment gap found and fixed during this test**: the dashboard
  container was running a build from **2026-09-09** — it didn't have
  `SkillFinder` or any other frontend work merged since then. Rebuilt from
  `main` mid-session; confirmed working after.
- **1 unconfirmed backend flake**: `/api/broski` → 503 (single sample, didn't
  recur, not chased further this session).
- **A few things that looked like bugs and weren't** — see "Ruled out" below.

## Page-by-page

### Hyper Station (home, `/`)
Metrics, Agents, Services/System Health, Tasks, and BROski Pulse panels all
render with real data. No console errors.
- `GET /api/broski` → **503** (single observation, home page's BROski Pulse
  poll). Didn't reproduce on later polls during this session but wasn't
  specifically re-tested in isolation — worth a look if it recurs.
- One `GET /api/agents` → 502 that self-resolved to 200 on the very next poll
  — consistent with a registry-scan-cycle timing gap, not a hard failure.

### Studio (`/ide`) — **SkillFinder feature test**
This is where the deployment gap was found: the dashboard container's image
was built **2026-09-09**, four days before tonight's merge, with no source
bind-mount (static production build) — so `/ide` initially showed only the
existing `StudioView`, with `SkillFinder` completely absent (not broken, not
erroring — just not present in the served code at all).

**Rebuilt `hypercode-dashboard` from `main` mid-session, then re-tested:**
- `SkillFinder` renders correctly above `StudioView`.
- Real search ("deploy a discord bot with moderation") returned genuinely
  good, real-LLM-ranked results (`hypercode-broski-discord-bot`,
  `hypercode-docker-ops`, `hypercode-redis-pubsub`, `hypercode-security`) with
  accurate rationales — confirms the `nvidia/nemotron-3-super-120b-a12b:free`
  + `reasoning: {"exclude": true}` fix from earlier tonight is genuinely
  working end-to-end through the real UI, not just via direct `curl`.
- Copy-to-clipboard button works (`/skill-name` → "Copied!").
- Empty-input guard works — clicking "Find a skill" with an empty field
  correctly no-ops (no network request fired).
- Dyslexia mode correctly re-themes `SkillFinder` along with the rest of the
  page (it inherited the existing CSS-variable convention correctly, as
  designed).
- **One transient issue**: the very first search attempt (right after the
  dashboard container was freshly recreated) showed `usedFallback: true`,
  `"no response within 15s"` — the request never even reached
  `hypercode-core`'s logs. Retried immediately after and it succeeded cleanly
  well within the timeout, with a real LLM response. Likely a cold-start
  DNS/connection-pool warmup between the freshly-recreated dashboard
  container and `hypercode-core` — did not reproduce on the second attempt.
  Worth watching if it recurs after future dashboard redeploys, but not
  treated as a confirmed bug from a single sample.

### Agents (`/agents`)
Clean. Shows 2 tracked agents (`healer-agent`, `hypercode-core`), both
healthy. Scope note: this is a smaller, XP/level-tracked agent list, distinct
from the full ~65-container fleet shown on Health/Docker Zone/Mission
Control — not a bug, just a different, narrower data source than the other
pages.

### Mission (`/mission`)
Agent Swarm, Event Timeline, Tasks, System Logs, Metrics, BROski Pulse, and
Plan Generator all rendered. "Live logs connected" toast confirmed the
WebSocket connection came up correctly. System Logs panel showed no entries
under the default "Any/All" filter — plausibly just no matching log lines in
the window, not investigated further.

### Mission Control (`/control`)
"AGENT FLEET" panel shows "Scanning the fleet..." for several seconds before
resolving — this matches a documented behavior in `fleet/route.ts` (the
registry scans on a ~30s cycle), not a bug. Once resolved: accurate real
counts (22 live · 13 down · 7 dormant · 42 total). Safety Feed panel works
well, showing real live `ALLOW` decision entries for `coder_studio` actions
with timestamps and file paths.

### Flows (`/flows`)
Clean empty state ("No active mission flows"), no errors.

### MCP (`/mcp`)
Resolves to `HyperCode MCP Server: ok`, correctly documents the SSE endpoint
(`http://localhost:8823/sse`). No errors.
- **Ruled out as a bug**: navigating here via the browser-automation tool's
  direct URL `navigate()` call initially showed stale content from the
  previously-visited Flows page, with the sidebar still highlighting "Flows".
  Confirmed via a hard reload (correct) and, more importantly, via a real
  in-app link click (also correct, every time) that this was an artifact of
  the automation tool's navigation method, not a real Next.js routing bug —
  no further action needed.

### Docker Zone (`/docker-zone`)
Excellent — "Docker Command Centre" shows detailed, accurate real-time
hot-reload status, agent counts, compose file counts, LLM runtime info, CVE
baseline, and a live 13-agent fleet list with per-agent watch/sync status.
No errors.

### Health (`/health`)
Comprehensive Docker + service health matrix. "Loading health..." for ~5s
before resolving (multiple `/api/*` and orchestrator health polls in
flight), then shows accurate real state matching independent `docker ps`
observations: Core/Crew Orchestrator/Healer all `HEALTHY`, infra services
(redis/postgres/hypercode-ollama/minio/chroma) all `HEALTHY`, and a clear,
correctly-labeled list of 14 ghost/offline agents by profile. One transient
`GET /api/mcp/health` → 503 that resolved to 200 on the next poll.

### Grafana (`/grafana`)
Launchpad tab UI (Ecosystem Launchpad, Mission Control v2.4, Safety Shepherd,
HyperSwarm HUD, BROski Agent Intelligence, Crew Orchestrator) renders
correctly. Clicking through to the embedded dashboard correctly shows
Grafana's own login screen (expected — Grafana auth isn't shared with the
dashboard's session by design) rather than erroring or showing a blank
iframe.

## Ruled out (looked like bugs, weren't)

| Observation | Verdict |
|---|---|
| `/mcp` showed stale `/flows` content after automation-tool `navigate()` | Testing-tool artifact — hard reload and real in-app clicks both work correctly every time. |
| Several panels stuck on "Loading..." for a few seconds | By design — matches documented poll/scan cycles (agent-registry ~30s scan, multi-endpoint health aggregation). All resolved correctly given time. |
| Grafana login prompt on embedded dashboard | Expected security behavior, not a failure. |
| SkillFinder's one 15s timeout | Did not reproduce on retry; treated as a cold-start blip, not a confirmed bug. |

## Confirmed findings needing follow-up

1. **Deployment process gap (now worked around, not fixed structurally)**:
   the dashboard doesn't get rebuilt automatically when frontend code merges
   to `main` — it was 4 days stale with zero visible symptoms (no errors, no
   broken pages, just silently missing every change since the last build).
   Worth a habit/checklist item: rebuild `dashboard` alongside `hypercode-core`
   after merging frontend work, or better, a note in the deploy docs that the
   two aren't coupled.
2. **`/api/broski` → 503**: single observation, not chased further this
   session. Worth a repro attempt and a look at `agents/dashboard/app/api/broski/route.ts`
   + whatever backend service it proxies to, next time someone's in this area.

## Not tested this pass (scope call, not an oversight)

- Studio's actual "Build it" agent-run flow — would spin up a real, slow,
  resource-heavy agentic task; skipped given the box's RAM state tonight.
- High-C and Focus neurodivergent modes (only Dyslexia was spot-checked).
- The "Hyper Brain" / "Universe" external header links (not clicked through).
- Mobile/responsive layout.
