# HyperCode IDE — Full UI Review Report

**Date:** 2026-09-08 (reviewed ~01:20–01:47 BST)
**Reviewer:** Perplexity session (external eyes, first full tour)
**Context:** Post Docker level-up day (5 commits: baseline → DMR spike → shim cutover, 588a57db latest). 38 containers live.

---

## Scope

| Page | URL | Reviewed |
|---|---|---|
| Hyper Station (Home) | `/` | ✅ |
| Studio | `/ide` | ✅ |
| Mission | `/mission` | ✅ |
| Mission Control | `/control` | ✅ |
| MCP | `/mcp` | ✅ |
| Docker Zone | `/docker-zone` | ✅ |
| Health | `/health` | ✅ |
| Grafana | `/grafana` | ✅ |
| Agents | `/agents` | ❌ not toured |
| Flows | `/flows` | ❌ not toured |

---

## Verdict

**The IDE is real.** This is not a dashboard demo — it is a working control surface over a live 38-container autonomous platform, with governance, observability, safety, and execution surfaces all present and mostly honest about system state. The gap between "product vision" and "product" is now mostly polish and three backend seams, not architecture.

**Overall: 7.5/10 as a product, 9/10 as a personal ops platform.**

---

## Page-by-Page

### 1. Hyper Station (Home) — 7/10
**Strengths:** Clean nav across the whole universe (Hyper Brain, Studio, Agents, Mission, Mission Control, Flows, MCP, Docker Zone, Health, Grafana). Neurodivergent mode strip (Default / Dyslexia / High-C / Focus) is a genuine differentiator — nobody else has this. Metrics/Agents/Tasks/Services/Pulse chunking is ADHD-friendly.

**Issues:**
- **Tasks panel: "Could not validate credentials"** — the single most damaging message on the platform. It blocks action, not just observation.
- Error rate showed 14.29% — needs classification (expected 403s vs real failures) before it means anything.
- Services panel shows 0 ms for everything — currently indistinguishable from a placeholder. It hides state instead of showing it.

### 2. Studio (`/ide`) — 8/10 — **the money page**
**Strengths:** The clearest expression of what HyperCode *is*: task → model → agent stream → diff review → merge. "Nothing touches your working tree until you merge" is the best single line of copy in the product. Throwaway worktree + Safety Shepherd gating = the safety story is real, and the page says it in plain English.

**Issues:**
- Empty states don't guide: a first-time user stares at a blank textarea with no example of "good."
- No run metadata surfaced (repo, worktree/branch, model, Shepherd state, elapsed) — it's a mystery box until proven otherwise.
- **Fix:** golden-path sample task button + compact run header. Highest ROI polish on the platform.

### 3. Mission (`/mission`) — 7.5/10
**Strengths:** The ops nerve-centre. Agent Swarm + Event Timeline + Metrics + Tasks + Logs + Plan Generator in one view. Event Timeline showed genuinely live activity (healer-agent `alert_only` runs) — real mission-control energy.

**Issues:**
- Same Tasks credential block, now with a live queued task behind it.
- Logs show repeated `GET /api/v1/ops/dlq` → **403** from hypercode-core — the auth seam again.
- 22.22% error rate (likely inflated by those 403s — but nobody knows because they're unclassified).
- Orchestrator health calls taking 2.5–4.4 s — watch before load grows.

### 4. Mission Control (`/control`) — 8.5/10 — **the governance heart**
**Strengths:** The Safety Feed makes the Governor visible: allow/escalate decisions with agent, tool, target, and reason. `fleet-controller` escalated on dangerous docker category; `governor` correctly blocked on ungranted `compose_profile.preview`. **This is Aug-24's lesson, enforced and visible.** Truth-first, not pretty-first.

**Issues:**
- **"Registry unreachable: TimeoutError"** — the fleet panel, on the page called Mission Control, is the least reliable panel. Priority fix.
- Feed is dense audit-log energy. Needs operator-first buckets: *Awaiting approval / Allowed today / Policy misconfig* + status strip (fleet reachable, pending approvals, dangerous blocked today, last policy sync).

### 5. MCP (`/mcp`) — 5/10 (blocked backend, honest UI)
**Strengths:** Clear, focused, honest — says exactly what the endpoint should be (`http://localhost:8823/sse`) and that the server is down.

**Issues:**
- **HyperCode MCP Server: DOWN.** This is the known `mcp-gateway Exited (1)` from the level-up day — still undiagnosed. High product surface, currently proving unavailability. Logs-first, no UI polish until it's up.
- Once healthy, page wants a tools list / recent calls preview — a binary up/down probe isn't enough.

### 6. Docker Zone (`/docker-zone`) — 7/10
**Strengths:** Punchy status strip (hot-reload live, 13 agents, 13+ compose files, ~1 s sync) + copy-paste command blocks (`up --watch`, `docker debug`, `develop.watch`). Practical, not decorative.

**Issues:**
- **"Docker Scout / Security — Already ahead ✓" is stale and too optimistic** — the actual story is a 24C/224H baseline captured today with a fix order pinned. The badge now *undersells* the day's work.
- Mixed mental model: part status board, part tips page, part upgrade checklist. Split cards into **Done / Live now / Next experiment** and show today's real wins (944 KiB shim, 5m unload, CVE baseline).

### 7. Health (`/health`) — 8.5/10 — **the truth panel**
**Strengths:** The most useful page on the platform. Groups Infra / Core / Observability / Proxy / Agents. The **"Offline agents (compose vs live)"** block with recovery command (`docker compose --profile agents up -d`) is exactly right — distinguishes "broken" from "not started." Observability stack fully healthy (Prometheus, Grafana, Loki, Tempo, Alertmanager, exporters). Core backbone healthy (Redis, Postgres, MinIO, Chroma, hypercode-core, healer, socket proxies).

**Issues:**
- **UNKNOWN floods the agent fleet** (crew-orchestrator, coder-agent, project-strategist, mcp-gateway, hyper-* agents, mission services). UNKNOWN vs OFFLINE-by-profile semantics need tightening — right now it reads as possible failure when it's mostly profile state.
- **Crew Orchestrator DEGRADED — `TypeError: fetch failed`** — the sharpest real fault on display.
- Stale label: `hypercode-ollama` still reads "Ollama" — it's now a 944 KiB socat shim → Docker Model Runner. Rename it.

### 8. Grafana (`/grafana`) — 8/10
**Strengths:** Doesn't fake Grafana — embeds the real thing with Pop out to :3001. The dashboard inventory is genuinely strong and domain-matched: BROski Agent Intelligence, HyperSwarm Mission Dashboard, **Safety Shepherd — Policy Decisions**, Mission Control v2.4, Tier 3 Pools & Queues, Smoke Metrics (Crew Orchestrator). UI surfaces and observability surfaces are aligned — that's rare discipline.

**Issues:** It's a wrapper + list. Wants 3–5 pinned quick-launch cards with one-line "use this when…" reasons, and a prefilled default board (Mission Control or Ecosystem Launchpad).

---

## Cross-Cutting Findings

### 🔴 Priority 1 — The auth seam (one bug, three symptoms)
Tasks unavailable ("Could not validate credentials") on Home + Mission, and the 403 DLQ spam in logs, all point at the same credential/permission boundary. Fixing this one seam unblocks the platform's only action path and deflates the error-rate numbers. **This is the next session's first job.**

### 🔴 Priority 2 — MCP server down
Known, undiagnosed since the level-up day, and it's a headline product surface. 15 minutes of `mcp-gateway` logs. No UI work until it's healthy.

### 🟠 Priority 3 — UNKNOWN vs OFFLINE semantics (Health)
Tighten agent state resolution so "not started under this profile" stops masquerading as "possibly broken." Also chase Crew Orchestrator's `fetch failed`.

### 🟠 Priority 4 — Registry timeout (Mission Control)
Fleet panel must be the most reliable panel on Mission Control. It currently isn't.

### 🟡 Priority 5 — Classification & polish
- Classify 403s as "protected, expected" vs real failures (fixes the scary 14–22% error rate display).
- Studio: sample task button + run metadata header.
- Mission Control: Safety Feed operator buckets + status strip.
- Docker Zone: replace stale "Already ahead" with today's real baseline numbers.
- Rename the `hypercode-ollama` label to reflect shim + Model Runner.
- Grafana: pinned quick-launch cards.

---

## What I Think of It All

**Honest assessment:** this is a platform with real bones. The three things that make it credible rather than a hobby dashboard:

1. **Governance is visible, not theoretical.** The Safety Feed showing real allow/escalate/block decisions — with reasons — is more than most production systems expose. Aug-24 happened once; the system now shows you the fences.
2. **Observability is aligned with the product.** Mission Control, Safety Shepherd, HyperSwarm, agent health — every UI surface has a matching Grafana board. When something breaks, you already know where to look.
3. **The pages tell the truth.** Down MCP, unreachable registry, UNKNOWN fleets, 403s in logs — the UI reports reality instead of performing health. That's the hardest discipline in ops tooling and you already have it.

The platform's biggest risk isn't architecture — it's that the **action path (Tasks)** and **integration path (MCP)** are both currently blocked, which makes the IDE a very good observer and not yet an operator. Close those two seams and the story flips: task → gated agent → reviewed merge, all inside your own neurodivergent-first IDE.

The neurodivergent mode strip (Dyslexia / High-C / Focus) across every page remains the differentiator nobody else has. Lean on it.

---

*Reviewed live at http://127.0.0.1:8088 — 8 pages, ~30 minutes, post-level-up-day state.*
