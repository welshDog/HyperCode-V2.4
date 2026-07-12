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

> ✅ Done this session (2026-07-12): **Crew-orchestrator safety intercept** (25/25 tests, monitor mode live, flip `SAFETY_SHEPHERD_MODE=enforce` when ready) · **Mission Control `/control` first screen** (fleet grid + safety feed, 6 vitest green — needs next build image rebuild at stack-down window) · **PITCH-KIT.md** (LinkedIn headline + freelance pitch + CV bullets + proof links in `HperCore/docs/`)

---

## ⏳ Stack-Down Window Queue (~15 min when RAM allows)

| Step | Action |
|---|---|
| 1 | **Bro runs** (permission-gated for Claude): `python scripts/mint_agent_keys.py safety-shepherd \| docker exec -i postgres psql -U postgres -d hypercode` — script already knows `safety-shepherd`; raw key lands in `secrets/agent_api_key_safety-shepherd.txt` |
| 2 | Tell Claude "key minted" → wires `docker-compose.secrets.yml` (CORE_AGENT_KEY_FILE convention, same as crew-orchestrator) — NOT wired yet on purpose: compose fails if the secret file doesn't exist |
| 3 | Rebuild shepherd image → governance-ledger writes go live (HS-P2c) |
| 4 | Rebuild dashboard image → `/control` Mission Control goes live (image on disk is from BEFORE the /control code — that's why it 404s) |

> 🔎 2026-07-12 late check: safety-shepherd had been **OOM-dead (exit 137) for 8h** — silently, because every gate fails open. Restarted + healthy. The `/control` safety feed makes this visible in future.

> ⚠️ Sacred rule: never rebuild images when <1GB RAM free. Check with `wsl -e free -m` first.

---

## 🏗️ HyperStudio — the agent write path

| # | Task | Status |
|---|---|---|
| HS-P1 | **Phase 1: the write path** — coder-studio :8087, Studio UI at `/ide`, model picker, merge-collision 409 | ✅ **Done 2026-07-10** (PR #315) |
| HS-P2a | **Interactive ESCALATE approval** — approve/deny gate, ApprovalModal + Redis channel | ✅ **Done 2026-07-11** (PR #316) |
| HS-P2b | **Specialist agents roster** — 8 already UP & healthy 7h+; security-engineer worth adding (RAM permitting) | ✅ **Mostly alive** (brief was stale) |
| HS-P2c | **Governance-ledger write of each verdict** — 32/32 tests green | ✅ **Done 2026-07-12** (awaiting deploy) |
| HS-P3 | **Crew-orchestrator → Shepherd intercept** — `safety_gate.py`, 25/25 tests, monitor mode live | ✅ **Done 2026-07-12** |
| HS-P4 | **Mission Control `/control` screen** — fleet grid (42 agents), safety feed, ApprovalModal | ✅ **Done 2026-07-12** (awaiting image rebuild) |

> 🏁 **Full safety loop CLOSED.** HyperFlow ✅ Studio ✅ Crew-orchestrator ✅

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
| P2-4 | **Course "AI Agents 2.0" track (M11+)** | ⬜ **NEXT — fresh session** |

> 🏁 AGENT-START roadmap: P0 · P1 · P2-1/2/3 all SHIPPED. P2-4 is the final piece.

---

## 💼 Job / Revenue (zero-cost actions)

| Action | Status |
|---|---|
| Paste LinkedIn headline from PITCH-KIT.md | ⬜ Do tonight (10 min) |
| Pin HyperCode-V2.4, welshdog.shop, MIND VAULT on GitHub profile | ⬜ Do tonight (5 min) |
| Companies House registration (£50, ~24h, SIC 62012) | ⬜ Human gate → unlocks Stripe LIVE |
| T&Cs + privacy + refund pages on welshdog.shop | ⬜ Code-ready when Companies House lands |
