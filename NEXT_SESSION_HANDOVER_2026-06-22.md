# 🧠 NEXT SESSION HANDOVER — 2026-06-22

> Generated: Monday 22 June 2026, BST
> Status: STACK HEALTHY ✅ — dashboard fixes shipped

---

## ✅ What Was Done This Session

- **Triaged a stale "core OOM / creds broken / 53% error" rescue brief** — almost all of it was false. Live `hypercode-core` was `Up (healthy)` the whole time (no OOM, RestartCount 0, `credsStore: desktop` working, ~40 containers up). `agent-registry` is a live service, not an orphan.
- **Real fix #1 — celery-worker:** was stuck in `Created` (never started). `docker start celery-worker` → running + healthy (connected to redis, ready). The one genuine gap.
- **Real fix #2 — dashboard route aliases:** added 307 redirects in `agents/dashboard/next.config.ts`: `/docker → /docker-zone`, `/grafana → /pricing` (URL bar updates; not rewrites). Brief's "404s" were just wrong URLs — real pages always existed.
- **Real fix #3 — IDE Files panel** (`agents/dashboard/components/views/IDEView.tsx`): removed the broken `/` button (filesystem MCP server is sandboxed to `/workspace`, so `/` deterministically 502s "unknown tool"); error message now surfaces the real upstream reason instead of always claiming "MCP adapter offline". The workspace was never actually empty — `/workspace` returns 270 entries, 6/6 stable.
- **Targeted dashboard-only rebuild** → both core + dashboard healthy; redirects + IDE fix verified live.
- `docs/STATUS.md` updated; obs bring-up report committed.
- **Commits pushed to `origin/main`:** `7bd308a` (fix) + `5797867` (docs). Tree clean.

---

## 🔥 In Progress / Next Up

1. ✅ Handover file (this)
2. 🟢 Nothing blocking — stack healthy, all fixes live & pushed.
3. ⚪ Optional: the 9 specialist/crew agents (`coder-agent`, `crew-orchestrator`, `devops-engineer`, etc.) sit in `Created` by design (on-demand / known-stale per prior sessions). Bring up only if a task needs them.
4. ⚪ Optional: `OBS_STACK_BRINGUP_REPORT` notes a Grafana password-wiring gap already resolved — no action.

---

## 🪤 Gotchas Discovered (load-bearing)

- **The REAL exit-137 trigger:** `docker compose up -d dashboard` cascades a RECREATE to its dependency `hypercode-core`. During the swap, old+new core briefly coexist and core OOM-exits 137 at the **~4.8 GB Docker ceiling** (`MemTotal=5157658624`), then self-recovers. 137 = memory churn, NOT creds/build.
  - **To rebuild dashboard with no core blip:** rebuild the image, then `docker restart hypercode-dashboard` (or `up -d --no-deps dashboard`). Do NOT plain `up -d dashboard`.
- **Dashboard is a baked `output: standalone` prod image** — frontend edits need an image rebuild (no hot reload). Real source lives at `agents/dashboard/` (NOT the sparse top-level `dashboard/`).
- **Dashboard route map:** `/docker-zone`, `/pricing` (= the "📈 Grafana" nav link), `/ide`. Port 8088 = the Next.js dashboard, NOT the core API (core health is internal `GET /health`).
- **Trust live `docker ps` / `docker inspect` over any rescue brief** — briefs on this stack recycle old incident symptoms.

---

## 🏗️ System State

- HyperCode-V2.4: ~40 containers up + healthy; 9 on-demand agents intentionally `Created`.
- core + dashboard + celery-worker: all healthy. Docker mem ceiling ~4.8 GB (OOM-sensitive during churn).
- Canonical compose: 4 files (`docker-compose.yml` + `secrets` + `registry` + `hyperhealth`) — NEVER pass `agents.yml` (already include:d). Prefer `.\hyperlaunch.ps1`.

---

## ⚡ Sacred Rules Reminder

- NEVER docker.io — always docker-ce-cli
- NEVER `from backend.app.X` — always `from app.X import Y`
- NEVER commit `.env` files
- Stripe webhook is ALWAYS rate-limit exempt
- Python indent: 4 spaces ONLY
- Redis DB1=cache, DB2=rate limits — NEVER mix
- `git fetch` + rebase before push — NEVER force-push
- Surface contradictions — never silently pick a side

---

## 🎯 Hyperfocus Zone Mission

> Building the world's first neurodivergent-first autonomous AI infrastructure platform.
> Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥 | @welshDog | BROski♾️
