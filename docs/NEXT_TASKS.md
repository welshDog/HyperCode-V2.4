# 🎯 Active Next Tasks
> Update this every session. Completed items → `WHATS_DONE.md`.
> For sacred rules + architecture → `CLAUDE.md`

---

| # | Task | Priority |
|---|---|---|
| 1 | **BROskiPets Web3 E2E** — test mint on Base Sepolia testnet (MetaMask = human gate) | 🟡 This week |
| 2 | **Fix GitHub Actions billing lock** — github.com/settings/billing (human gate) | 🟡 |
| 3 | **Discord Bot Tier 2** — Pets, XP Leaderboard, Morning Briefing, Health Alerts | 🟢 Background |
| 4 | **HyperLabs human gates** — Vercel Speed Insights CWV · `/pets` wallet smoke · post-login reconcile | 🟢 Human gate |
| 5 | **`/welcome` auth-gate decision** — make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| 6 | ~~**Wire BROski$ XP to postgres**~~ ✅ **DONE 2026-06-18** | ✅ Done |

> ✅ Code done this session (2026-07-12): Crew-orchestrator safety intercept (25/25 tests) · Mission Control `/control` screen (6 vitest green) · HS-P2c governance-ledger write (32/32 tests) · PITCH-KIT.md
> ⚠️ **Deploy pending** — two images need a stack-down rebuild before code goes live (see queue below)

---

## 🚨 Important Find — 2026-07-12 Late Check

> **safety-shepherd was OOM-dead (exit 137) for ~8 hours.** Silent failure — every gate fails open by design, so the ecosystem ran ungated all evening. Restarted + healthy now (`api_key_configured: true`, manifest loaded).
>
> 💡 Root cause: build ran while stack was up → engine OOM → Shepherd killed as collateral. The `/control` safety feed will make this **instantly visible** in future — a dead Shepherd dot on the fleet grid can't be missed.

---

## ✅ Deploy Window COMPLETE — 2026-07-13 ~00:15

| Step | Result |
|---|---|
| Key minted + `docker-compose.secrets.yml` wired (CORE_AGENT_KEY_FILE convention) | ✅ |
| Rebuilt **3** images: safety-shepherd, dashboard, **hypercode-core** (core was the missed one — the POST /governance/ledger endpoint ships in the core image; core has NO app bind-mount) | ✅ |
| Stack restored: 38 containers, core recreated on new image, all healthy | ✅ |
| **E2E PROVEN**: `/evaluate` → `governance_ledger` rows (`safety.file_read ALLOW` + `safety.generic ESCALATE`, `approved_by=safety-shepherd`) + `safety_ledger_pushes_total{status="ok"}` | ✅ |
| `/control` Mission Control | ✅ **HTTP 200 — LIVE** at localhost:8088/control |

> 🪤 Lesson: cold-start bring-up OOM-killed hypercode-core once (exit 137) — staged restart fixed it. First ledger push against a cold core timed out (3s) → counted `status="error"`, fail-soft worked as designed.

---

## 🏗️ HyperStudio — the agent write path

| # | Task | Status |
|---|---|---|
| HS-P1 | Phase 1 write path — coder-studio :8087, `/ide` UI, model picker | ✅ Done 2026-07-10 (PR #315) |
| HS-P2a | Interactive ESCALATE approval — ApprovalModal + Redis channel | ✅ Done 2026-07-11 (PR #316) |
| HS-P2b | Specialist agents roster — 8 healthy; security-engineer optional (RAM permitting) | ✅ Mostly alive |
| HS-P2c | Governance-ledger write — 32/32 tests green | ✅ Code done ⚠️ awaiting deploy |
| HS-P3 | Crew-orchestrator → Shepherd intercept — 25/25 tests, running healthy | ✅ LIVE |
| HS-P4 | Mission Control `/control` screen — fleet grid + safety feed | ✅ Code done ⚠️ awaiting image rebuild (404 until then) |

> 🏁 Safety loop code complete: HyperFlow ✅ Studio ✅ Crew-orchestrator ✅ — needs deploy to be fully live.

---

## 🔴 P0 — Control Plane

| # | Task | Status |
|---|---|---|
| P0-1 | HyperFlow | ✅ Done 2026-06-19 |
| P0-2 | Safety Shepherd Agent | ✅ Done 2026-06-19 |
| P0-3 | Mission Graph Dashboard Panel | ✅ Done 2026-06-19 |

## 🟡 P1 — Identity + Governance

| # | Task | Status |
|---|---|---|
| P1-1 | BROski Identity Agent | ✅ Done 2026-06-19 |
| P1-2 | Governance Ledger | ✅ Done 2026-06-19 |
| P1-3 | Extract skills to HYPER-SILLs vault | ✅ Done 2026-06-19 |
| P1-4 | Fill specialist HYPER-AGENT-BIBLEs | ✅ Done 2026-06-19 |

## 🟢 P2 — Continuous Evolution + Course

| # | Task | Status |
|---|---|---|
| P2-1 | Evo Harness | ✅ Done 2026-06-20 |
| P2-2 | Brain Constellation Level 20 | ✅ Done 2026-06-20 |
| P2-3 | Brain Levels 18 + 19 | ✅ Done 2026-06-20 |
| P2-4 | **Course "AI Agents 2.0" track (M11+)** | ⬜ NEXT — fresh session |

> 🏁 AGENT-START roadmap: P0 · P1 · P2-1/2/3 all SHIPPED. P2-4 is the final piece.

---

## 💼 Job / Revenue (zero-cost)

| Action | Status |
|---|---|
| LinkedIn headline from PITCH-KIT.md | ✅ Done 2026-07-12 |
| Pin repos on GitHub profile | ✅ Done 2026-07-12 |
| Companies House registration (£50, SIC 62012) | ⬜ Human gate → unlocks Stripe LIVE |
| T&Cs + privacy + refund pages on welshdog.shop | ⬜ Code-ready when Companies House lands |
