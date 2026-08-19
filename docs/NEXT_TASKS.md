# 🎯 Active Next Tasks
> Update this every session. Completed items → `WHATS_DONE.md`.
> For sacred rules + architecture → `CLAUDE.md`
> Last updated: **August 19, 2026**

---

## 🔥 Immediate — Do These First

| # | Task | Priority |
|---|---|---|
| 1 | **Verify no port clashes** — `grep -r "ports:" docker-compose*.yml \| sort` | 🔴 Before launch |
| 2 | **Launch 25-agent fleet** — `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d` | 🔴 After builds complete (~30–60 min) |
| 3 | **Add resource limits** to all 12 new agents (`mem_limit: 256m`, `cpus: "0.25"`) | 🔴 Before launch |
| 4 | **Verify crew-orchestrator** has `restart: unless-stopped` + `/health` endpoint | 🔴 Before launch |

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
| Metrics error-rate cosmetics | — | "Error Rate ~54%" perma-red — fix when next touching metrics |

---

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
