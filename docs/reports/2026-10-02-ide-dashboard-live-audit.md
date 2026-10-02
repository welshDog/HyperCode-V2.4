# HyperCode IDE (hypercode-dashboard, :8088) — Live Audit

**Date:** 2026-10-02 · **Tested by:** Claude, live in-browser (Claude-in-Chrome) + direct `curl`/`docker exec`/source read against the real running stack (44/53 containers up, `hypercode-dashboard` healthy 8+ min). Every finding below is reproduced live, not inferred from code reading alone, unless marked "not executed" (destructive/costly actions I stopped short of per safety rules).

**Headline:** one root cause — a broken service credential — breaks 3+ distinct features and causes a permanent background error-storm. Everything else found is real but smaller.

---

## 🔴 Fix #1 (do this first): service JWT is wired to the wrong value

**Symptom (live-reproduced):**
- "Tasks" panel → `DLQ unavailable — Could not validate credentials`
- Mission page → Plan Generator → `❌ Plan generation failed` / `⚠ Could not validate credentials`
- Browser console spams `[ApprovalStream] Error: Event` **every 5 seconds, forever**, across every page (169 occurrences observed in under 2 minutes, still firing after navigating away from the page that opens the connection)

**Root cause, verified end-to-end:**
1. `.env` (HyperCode-V2.4 root) line 214 already has a real, valid-looking signed JWT: `DASHBOARD_SERVICE_JWT=eyJhbGci...` (decodes to `{"sub":"9","exp":2104315652}` — a long-lived service account token).
2. `docker-compose.agents.yml:265` **overrides it**: `DASHBOARD_SERVICE_JWT=${HYPERCODE_API_KEY:-dev-master-key}`. Confirmed via `docker exec hypercode-dashboard printenv DASHBOARD_SERVICE_JWT` → the container actually gets `hc_b040f1e59a02ee4a2fd3624a7a7c6f631eb0b53651e8e63b0c4e1386031f7449` (the plain API-key string from `.env:218`, not a JWT).
3. `agents/dashboard/lib/server-auth.ts`'s `serviceAuthHeader()` sends this as `Authorization: Bearer hc_b040f1e...` to `hypercode-core`.
4. `backend/app/api/deps.py:get_current_user` runs `jwt.decode(token, settings.JWT_SECRET, ...)` on it — an API key is not a JWT, decode fails, raises `403 "Could not validate credentials"` every single time.
5. `agents/dashboard/app/api/ws-token/route.ts` (backing `ApprovalModal.tsx`'s live-approvals WebSocket) hands out the **same** broken string — confirmed via `curl http://127.0.0.1:8088/api/ws-token` → `{"token":"hc_b040f1e..."}`. The WebSocket handshake to `hypercode-core`'s `/ws/approvals?token=...` is rejected, `onerror` fires, `onclose` schedules a retry in exactly 5000ms (`ApprovalModal.tsx:80`) — forever, with no backoff and no max-attempts, and the component never unmounts across route changes.

**Fix:** in `docker-compose.agents.yml:265`, stop overriding `DASHBOARD_SERVICE_JWT` with `HYPERCODE_API_KEY`/`dev-master-key` — let it pass through the real JWT already sitting in `.env:214` (or generate a fresh one the same way and store it there). One-line compose change, no code change needed. After the fix, re-verify: `curl -s http://127.0.0.1:8088/api/ops/dlq/stats` should stop 403ing, and the `[ApprovalStream] Error` console spam should stop within 5s of a page load.

**Secondary fix, same component:** even after the credential is fixed, `ApprovalModal.tsx`'s reconnect loop has no backoff and no cap (`retryTimeout = setTimeout(connect, 5000)` unconditionally on every `onclose`). Add exponential backoff with a ceiling so a *future* real outage doesn't spam the console indefinitely again.

---

## 🟠 Fix #2: System Health panel reports unrelated, non-fleet Docker containers as "DOWN services"

**Symptom (live-reproduced):** Hyper Station's "System Health" widget shows a site-wide **CRITICAL** banner, listing `Sweet Bose`, `Priceless Hell...`, `Frosty Benz`, `Quirky Bose`, `Eager Engelbart`, `Frosty Einstein`, `Goofy Hoover`, `Exciting Solom...`, `Xenodochial J...` as DOWN "services".

**Root cause, verified:** these are random Docker-auto-generated container names (`docker ps -a` confirms: `Exited (255) 47 hours ago` / `Exited (2-3) 3 days ago`) — leftover one-off containers completely unrelated to the HyperCode fleet. `backend/app/api/v1/endpoints/orchestrator.py:get_system_health` (lines ~54–93) calls the Docker socket proxy's `/containers/json?all=1` with **no allow-list/roster filter** and reports every single container it finds, by its raw name, as a monitored "service." Anything that ever ran on this Docker host and exited pollutes this panel.

**Contrast:** the dedicated **Health** tab (`/health`) and **Mission Control** tab (`/control`) both get this right — they report a curated, real agent roster (42 total, correctly distinguishing "ghost agent, not deployed in this profile" from "actually down") with zero junk entries. `get_system_health` should filter against the same known-roster source those pages use (or at minimum exclude anything not matching a `hypercode.*`/known-agent naming convention) instead of enumerating the whole Docker host.

**Impact:** real specialist-agent downtime (which IS legitimate — `backend-specialist`, `frontend-specialist`, `qa-engineer`, etc. really aren't running in this profile) gets buried under false-positive noise, and the top-line "CRITICAL" status is misleading on every page load.

---

## 🟠 Fix #3: "Agents" board undercounts the real fleet by ~14x

**Symptom (live-reproduced):** Hyper Station's "Agents" panel and the dedicated `/agents` page both show **3 agents** (`celery-worker`, `healer-agent`, `hypercode-core`), while the same session's Mission Control (`/control`) and Health (`/health`) pages — querying different endpoints — correctly show **14 live / 42 total** real agents.

**Root cause, verified in source:** `agents/dashboard/app/api/agents/route.ts` deliberately calls `/api/v1/agents/status`, described in its own comment as "the OPEN heartbeat roster" — chosen over the auth-gated `/api/v1/orchestrator/agents` specifically to avoid a prior bug (silently rendering "no agents" on a 401). That trade-off is reasonable, but the heartbeat roster only contains processes that actively publish to `agents:heartbeat:*` in Redis (confirmed: `celery-worker`'s own `_celery_heartbeat_thread` in `backend/app/worker.py` is one of only three that do). Every other running agent (governor, crew-orchestrator, safety-shepherd, agent-registry, skillweaver, etc.) simply never shows up here.

**Fix:** point this widget at the same data source Mission Control already uses successfully (`/api/fleet`, backed by `agent-registry`'s `:8077 GET /agents/status` — unauthenticated, already proven reliable, already reports all 42). No need to keep maintaining two different "how many agents are there" answers in the same app.

---

## 🟡 Fix #4: every dashboard widget hard-fails instead of showing a loading state on first paint

**Symptom (live-reproduced):** On a fresh page load, `/api/agents`, `/api/tasks`, `/api/metrics`, and the direct `localhost:8000/api/v1/orchestrator/system/health` call all return **502/503 for the first ~10–15 seconds**, then settle to 200 with no backend restart or intervention — confirmed by polling the exact same URLs with `curl` a few seconds apart (200 OK both times) while the browser, in the same window, was showing hard red "Agent fleet unavailable HTTP 502" / "Tasks unavailable HTTP 502" boxes. This isn't a backend outage; the containers were already `healthy` the whole time.

**Impact:** every time someone opens this dashboard, it looks broken for the first ~15 seconds — no spinner, no "connecting..." state, just a bordered red error card identical in style to a real, permanent failure.

**Fix:** treat the first N failures after a route/page mount as "still connecting" (show a skeleton/spinner) and only escalate to the red "unavailable" state after a small number of consecutive failures or a longer timeout. This also reduces false alarms from the aggressive polling noted below.

---

## 🟡 Fix #5: aggressive, unthrottled global polling

**Observed:** `/api/agents` alone was called well over 20 times in under 60 seconds of browsing — and kept firing at the same cadence **while on unrelated pages** (Studio, Grafana) that don't visibly use that data, meaning the Hyper Station poller is mounted globally rather than only while its own widgets are visible. `/api/ops/dlq/stats` and `/api/ops/dlq` keep polling on the same cadence even though they have failed with the same 403 every single time since the page loaded — no backoff, no "stop polling a permanently-broken endpoint" logic.

**Fix:** scope pollers to the page/widget that actually renders their data (unmount the interval on route change), and add backoff (or at least a "stop after N consecutive identical failures, resume on manual refresh") for the DLQ calls specifically.

---

## 🟢 Minor / cosmetic

- **Mission page Metrics widget:** briefly rendered the literal text `⏳ Loading metrics...` (a raw, unescaped unicode code point) instead of an hourglass character before resolving ~4s later. Low priority, but a real string-escaping bug somewhere in that loading-state label.
- **Grafana tab:** embeds real Grafana (`:3001`) correctly, but requires a **separate login** inside the iframe (not SSO'd with the dashboard's own session) — a real "Welcome to Grafana / email+password" form appears every time. Minor friction, not a bug, but worth a credential hint or SSO if this gets used often.
- **Studio tab model picker:** self-documents "Free / Local = slower, cheaper, private — wiring in progress" — a known, intentionally-flagged incomplete feature, not a new finding, just confirming it's still true live.
- **Docker Zone tab:** shows a Docker Scout CVE baseline card reading "24 CRITICAL · 224 HIGH," dated "captured 2026-09-07" (~3.5 weeks stale as of this audit). Not a dashboard bug, but worth a fresh `docker scout` pass if that baseline hasn't been rechecked since.

---

## Not tested (stopped short deliberately)

- **Grafana embedded login**: did not attempt credentials (per the "no entering passwords" rule) — confirmed the form renders and is reachable, not that login succeeds.

## Addendum (2026-10-02, later same day): Studio "Build it" executed live

Per Bro's go-ahead, actually ran the Build-it pipeline end-to-end (session `cs_80aebc51257a`, model Haiku 4.5, task = the built-in `/healthz` sample). Two real issues found and fixed in pre-flight, one real finding from the run itself, one new separate finding left unfixed.

**Pre-flight fix — `coder-studio` was silently pointed at the free proxy, not Anthropic.** The running container had `docker-compose.studio-fcc.yml`/`docker-compose.fcc.yml` applied (`ANTHROPIC_BASE_URL=http://fcc-proxy:8083`, `ANTHROPIC_API_KEY=freecc`), a leftover from a prior free-tier test. That override only understands the disabled `nvidia_nim/...` model string — any of the UI's enabled Cloud models would have been sent to the wrong backend and failed. Fixed by recreating `coder-studio` with the standard 4-file compose set (`docker-compose.yml` + `.secrets.yml` + `.registry.yml` + `.hyperhealth.yml`, no fcc files), restoring real `sk-ant-...` routing: `docker compose up -d --no-deps safety-shepherd coder-studio`.

**Pre-flight false alarm, worth noting so it isn't re-chased later:** initially flagged `safety-shepherd`'s `API_KEY` env var as unset, matching a 2026-09-07 staleness incident in `WHATS_DONE.md`. That was checking the wrong variable — Shepherd actually reads `HYPERCODE_API_KEY`/`HYPERCODE_API_KEY_FILE` (`agents/safety-shepherd/safety_shepherd.py:218-225`), which was present and already matched `coder-studio`'s key both before and after the recreate. No actual credential mismatch existed this time.

**The run itself: pipeline works, Anthropic account doesn't currently have usable credit.** Session created, worktree prepared, SSE stream rendered live ("preparing sandbox" → "running"), terminal state reported correctly — then `GET /sessions/cs_80aebc51257a` confirmed `status: "review"`, `diff: ""`, `merge_sha: null`. The UI's live stream showed the actual cause: **"Credit balance is too low."** Shepherd counts stayed `0 ALLOW / 0 WARN / 0 BLOCK` — the agent never got a usable model response to act on, so no tool calls were ever attempted, no file was written, and no cost was incurred. This confirms the governed pipeline (session lifecycle, worktree isolation, Shepherd wiring, SSE streaming, terminal-state reporting) is fully functional; the blocker is the Anthropic account's credit balance, not a code defect. (`WHATS_DONE.md:636` records this exact "no Anthropic credit" condition happening once before, on 2026-09-09.) Session discarded cleanly via `POST /sessions/{id}/discard`; confirmed via `git worktree list` inside the container that no worktree was left behind for this run.

**New, separate finding — not fixed, flagging only:** `git worktree list` inside `coder-studio` shows **24 leftover agent worktrees/branches** going back across many past Studio runs (`agent/extract-the-retry-backoff-logic-*`, three separate `agent/add-a-healthz-route-*` from earlier test runs, several `agent/run-a-health-check-*`, etc.) — none cleaned up by their own merge/discard. This is a real, accumulating disk-space leak on the `studio-worktrees` Docker volume and suggests `discard`/`merge` haven't reliably pruned their worktree+branch in at least some historical runs. Worth a dedicated cleanup pass (`git worktree remove` + `git branch -D` for each stale `agent/*` entry) and a look at whether `worktree.py`'s cleanup path has a gap — out of scope for this audit, not touched.

**Bottom line:** Studio's "Build it" is real, governed, and safe (worktree isolation + Safety Shepherd both proved themselves live again) — but won't produce actual code changes until the Anthropic account has usable credit. Worth checking the billing dashboard before trying this again for real.

---

## Priority order

1. **Fix #1** (service JWT) — one-line compose fix, unlocks 3 broken features and stops a permanent console-error loop. Highest value, lowest effort.
2. **Fix #2** (System Health junk containers) — false CRITICAL banner undermines trust in the whole page; also low effort (add a roster filter, the correct roster already exists and is used elsewhere in the same codebase).
3. **Fix #3** (Agents undercount) — point at the already-working `/api/fleet` endpoint instead of the narrow heartbeat one.
4. **Fix #4 / #5** (loading-state UX + polling hygiene) — lower urgency, but cheap wins that remove the "looks broken on every load" first impression.
5. Minor items — whenever convenient.
