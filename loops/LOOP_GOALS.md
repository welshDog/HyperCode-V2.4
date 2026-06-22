# LOOP_GOALS.md — HyperCode-V2.4 Loop Backlog
> Ranked. Top = highest priority. Claude picks the first unblocked item.

---

> ⚠️ AGENT-START roadmap P0-1 → P2-4 is CLOSED (all 10 milestones built + pushed, 2026-06-22).
> The old queue (Catch Stragglers, L18/19/20) is all DONE — see below. This is the live backlog.

## 🔥 Priority Queue

| # | Goal | Success Test | Blocked? |
|---|---|---|---|
| 1 | Browser visual pass on dashboard `/ide` Files panel + `/docker-zone` + `/pricing` | All render clean, no console errors (Playwright/manual) | No |
| 2 | Grafana loop-history dashboard (loops/day, success rate) | Panel renders from LOOP_REGISTRY data | No |
| 3 | Wire Safety Shepherd intercept into HyperFlow/orchestrator | ESCALATE path fires on a guarded action | No |

---

## 🔒 Blocked on human gates (not code)

| Gate | Owner | Unblocks |
|---|---|---|
| GitHub billing | Bro | graph-refresh Actions + per-repo CI (incl. evo-harness) |
| Stripe LIVE | Bro | blocked on Companies House registration |
| Base Sepolia top-up | Bro | further pet mints / evolutions |

---

## ✅ Done (do not rebuild)
See `WHATS_DONE.md`. Roadmap milestones: HyperFlow · Safety Shepherd · Mission Graph panel · Identity Agent · Governance Ledger · HYPER-SILLs reconcile · Agent Bibles · Evo Harness · Brain Constellation L20 · Brain L18/19 · Course AI Agents 2.0 (M11–M13).

---

## 💡 Future Loop Ideas
- Auto-spawn new agent from manifest.json loop
- Grafana dashboard for loop run history
- Loop performance dashboard (loops per day, success rate)
