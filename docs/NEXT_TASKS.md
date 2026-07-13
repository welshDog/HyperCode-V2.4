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

> ✅ Done 2026-07-12/13: Crew-orchestrator safety intercept · Mission Control `/control` · HS-P2c governance-ledger write · PITCH-KIT.md · **Full deploy window: ALL LIVE + E2E PROVEN at 00:30 BST**
> ✅ **2026-07-13 ~09:45: ALL 8 PLAYTEST FIXES SHIPPED + VERIFIED LIVE** — Tailwind imported (`/control` styled) · agents roster truthful · service-JWT auth (task CREATE works E2E; core enum drift fixed with `values_callable`) · approvals WS "Connected" · focus mode isolates cleanly · `/control` in nav · health row honest · `/grafana` route (+ `/pricing` redirect). Report: `HperCore/docs/PLAYTEST-2026-07-13-mythos.md`
> ⬜ Residual (Bro's call): DLQ panel is superuser-gated and user 1 is `is_superuser=false`. To enable: `docker exec postgres psql -U postgres -d hypercode -c "UPDATE users SET is_superuser=true WHERE id=1"`

---

## 🏁 SAFETY STORY: 100% LIVE (2026-07-13 00:30 BST)

| Piece | Status |
|---|---|
| 🏛️ Mission Control `/control` | ✅ **LIVE** — `localhost:8088/control` 200, fleet grid + safety feed real |
| 📜 Governance-ledger writes | ✅ **LIVE + PROVEN** — `safety.file_read ALLOW` + `safety.generic ESCALATE` rows in DB, `approved_by=safety-shepherd` |
| 🛡️ Full safety loop | ✅ HyperFlow ✅ Studio ✅ Crew-orchestrator ✅ Ledger ✅ |
| 🐳 Stack | ✅ 38 containers healthy |

> 💡 **Lesson learned (in memory):** `hypercode-core` doesn't bind-mount — needs its own image rebuild when a new endpoint ships. First push hit 405 until core was rebuilt. Never bites again.
> 🛡️ **Fail-soft proven live:** cold-start timeout → `status="error"` metric tick, zero blocked decisions.

---

## ⏭️ Next Session — One Remaining Piece

| Task | Notes |
|---|---|
| **Course AI Agents 2.0 (P2-4, M11+)** | ⬜ Last item on the entire AGENT-START roadmap. Fresh session. `Hyper-Vibe-Coding-Course`. |
| **`/welcome` auth-gate decision** | Quick call — big sponsor UX win if made public. |
| **Companies House reg (£50, SIC 62012)** | Human gate → Stripe LIVE → first real £. |

---

## 🏗️ HyperStudio — all phases

| # | Task | Status |
|---|---|---|
| HS-P1 | Phase 1 write path | ✅ Done 2026-07-10 (PR #315) |
| HS-P2a | Interactive ESCALATE approval | ✅ Done 2026-07-11 (PR #316) |
| HS-P2b | Specialist agents roster | ✅ Alive |
| HS-P2c | Governance-ledger write | ✅ **LIVE** 2026-07-13 |
| HS-P3 | Crew-orchestrator → Shepherd intercept | ✅ **LIVE** 2026-07-12 |
| HS-P4 | Mission Control `/control` | ✅ **LIVE** 2026-07-13 |

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

---

## 💼 Job / Revenue

| Action | Status |
|---|---|
| LinkedIn headline + GitHub pins | ✅ Done 2026-07-12 |
| Companies House (£50, SIC 62012) | ⬜ Human gate → Stripe LIVE |
| T&Cs + privacy + refund pages | ⬜ Code-ready when reg lands |
