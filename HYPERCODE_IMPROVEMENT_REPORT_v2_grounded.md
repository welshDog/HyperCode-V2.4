# HyperCode Improvement Report — v2 (grounded)
## From "powerful stack" to "the calm loop that actually runs"

> **This is a sharpened, de-duplicated rewrite of `My Research Recommendations.md`.**
> The v1 report was strategically sharp but quoted health numbers it never checked. This
> version is **grounded against a live `docker ps` + endpoint probe on 2026-07-23**, cuts the
> repetition, adds the *stop-doing* half v1 was missing, and names a single wedge.
> Where v1 and reality disagree, reality wins (AGENT-START rule).

---

## 0. Reality check — what v1 claimed vs what's actually true

I checked, live, before writing a word:

| v1 claim | Live truth (2026-07-23) | So what |
|---|---|---|
| "32/32 containers healthy" | **3 running** — only `healer-agent` is a real stack service (healthy 14h); the other two (`intelligent_wiles`, `zealous_mccarthy`) are random-named orphans. **45 stopped**, 48 total. | The stack isn't a "serious running foundation" today — it's **parked**. |
| "77 Prometheus targets up… live OTLP traces in Tempo" | **Prometheus unreachable.** Grafana `:3001` → HTTP 000. Dashboard `:8088` → HTTP 000. The whole obs stack is **down**. | "We can measure real behaviour" is *aspirational*, not current. |
| "HyperCode has 25 agents" | **25 is the *defined* roster** in `docker-compose.agents-full.yml` — not running. `core`=7, `agents`=35, `brain`=7, `observability`=12 services. **20+ profile compose files.** | Capacity is real; **running footprint is ~zero.** |
| (unstated) | **8 GB RAM ceiling** (physical 7.8 GB). The full ~30-container stack **cannot run on this machine** — that's why `lean`, `nano`, `agents-lite` compose files exist. | The binding constraint isn't "build more." It's **"run what you have."** |

**The honest headline:** HyperCode has enormous *defined* capability and a near-zero *running* footprint, capped by hardware. "32/32 healthy" was a peak moment, not daily life.

---

## 1. The real diagnosis (reframed)

v1 said the gap is **capability → clarity**. True, but shallow. The deeper gaps, grounded:

1. **Capacity you can't run.** 20+ compose files and a 30-container design on an 8 GB box. The product that matters is the one that boots on the **lean profile** (a handful of containers) — because that's the only one a real user, on a real laptop, will ever see running.
2. **Capability scattered across repos, drifting.** The momentum primitives v1 says to "build" mostly **already exist, in pieces**: dev-XP git hooks (14 repos), Brain's morning-briefing (live :3304), Session Snapshot, and — see §3 — **two** copies of the Co-Pilot. The work is *consolidation*, not construction.
3. **No proof of human outcomes** (v1 got this right, keep it): infra health ≠ "is anyone finishing a task."

**Product rule (kept from v1, it's good):** hide system complexity by default; reveal Builder/DevOps modes only on request.

---

## 2. Keep these from v1 — they're genuinely strong

No need to reinvent. Carry forward, unchanged:

- **Sell outcomes, not agent access.** *"Unstick my bug safely"* > *"Buy 800 tokens for 11 agents."*
- **Action Cards** on every agent action: Goal · Why now · Risk · Cost · Proof · Undo.
- **The 0–4 autonomy ladder** — *with a change:* **default everyone to Level 0–1 (Explain/Draft).** Power is opt-in; calm is default. (v1 described the ladder but never set the default — that's the whole game.)
- **Experience metrics beside infra metrics** (Time-to-first-win, Overwhelm-escape-rate, Surprise-rate). Infra says *alive*; these say *helping*.

---

## 3. The ONE wedge — Co-Pilot ↔ HyperCode consolidation

**This is the single highest-leverage move, and it's already ~80% wired.**

Grounded facts:
- `docker-compose.brain.yml` **already defines `agent-hyperfocus-copilot`** — `nginx:alpine`, port **`:3305`**, profile `brain`, serving static files.
- v1's three modes — **Start / Build / Recover** — are *already prototyped* as the standalone `hyperfocus-copilot` PWA (6-state picker → freeze_rescue / focus_sprint / soft_recovery → "come back without shame"). Its core loop was verified working on 2026-07-23.

**⚠️ Drift trap found:** the running `agent-hyperfocus-copilot` serves from
`BROski-Obsidian-Brain/.../HYPERFOCUS_ZONE/07-Co-Pilot/public` — a **different copy** than the
standalone `hyperfocus-copilot/public` repo that got the 4 bug-fixes today. **These two must be
reconciled or the fixes don't reach the container.** (Verify before anything else.)

**The wedge:** make the Co-Pilot the **calm front door**, and let it drive HyperCode underneath.
- Co-Pilot = Start Mode + Recover Mode (exists, works).
- HyperCode swarm = the engine behind Build Mode (exists).
- XP hooks / Session Snapshot / Morning Briefing = surfaced *through the one calm surface*, not as 20 separate features (exist, scattered).

That's a smaller, more honest Phase 1 than v1's "build five agents in a month."

---

## 4. Stop-doing list — the half v1 completely missed

You cannot bolt calm onto complexity. Calm comes from **subtraction**:

- **Retire or freeze the redundant compose files.** 20+ is an ops overwhelm surface. Bless **one** default (`lean`), keep `agents-full` for demos, archive the rest with a README pointer.
- **Default the swarm OFF.** Ship at Level 0–1 autonomy with a handful of agents; the other ~20 are opt-in under "Builder Mode."
- **Kill the dashboard-first experience.** A new user should see **one "Today" screen** (Continue · Important · Easy win — v1's Morning Briefing, promoted to *be the app*), never raw service health.
- **Stop optimising the money loop until one loop is proven** (§5). No new plans, no marketplace, no visual pipeline studio yet.
- **Make subtraction a visible win:** *"Running 6 agents instead of 25 for you today."*

---

## 5. Realistic sequence (effort-estimated — NOT the v1 fantasy month)

v1's 30-day plan stacked ~9 features into weeks 2–3. For a solo neurodivergent builder that's a
quarter, not a month — and an overloaded roadmap *is itself* a betrayal of the thesis. Honest version:

| # | Move | Effort | Why first |
|---|---|---|---|
| 1 | **Reconcile the two Co-Pilot copies** (§3 drift trap) | ~1–2 hrs | Nothing else is real until the served copy = the fixed copy |
| 2 | **Prove the lean profile boots + Co-Pilot on `:3305`** | ~half day | The only stack a real user will run |
| 3 | **One "Today" screen** = Continue / Important / Easy win | ~2–3 days | The calm front door, using pieces that exist |
| 4 | **Wire Session Snapshot → "Welcome back, continue here?"** | ~2–3 days | The single most differentiating feature; recover-without-shame |
| 5 | **Micro-Achievement surfacing** (XP hooks already emit; just show them) | ~1–2 days | Fast visible wins, near-zero new code |
| 6 | **Verify ONE paid loop in Stripe TEST** (checkout→webhook→token→entitlement) | ~half day | ⚠️ *live* Stripe is blocked on Companies House — test-mode proof is the realistic goal now |
| 7 | Action Cards + autonomy default = Level 0–1 | ~3–5 days | Trust layer, once the loop exists |

Everything past #7 (Focus Panic polish, Human Momentum Dashboard, Questlines) waits for real usage data.

---

## 6. What I cut from v1, and why

- **Deduplicated:** BROskiPets-as-emotional-layer, the momentum dashboards, and the safety-net each appeared *twice* (Report + "8 ideas"). Folded to one mention each.
- **Parked (they fight "prove one loop first"):** #3 Visual Pipeline Studio and #6 Community Template Marketplace are each their *own product*. v1's own Phase 3 says don't build a marketplace before proving the loop — the idea list forgot that 40 lines later. Revisit post-#7.
- **Downgraded to "needs data you don't have yet":** the Brain Profile Engine and frustration-detectors (#2/#4) require behavioural signals + labelled sessions that don't exist. Good v2-of-*this* material, not now.
- **Kept whole:** the outcomes-not-tokens framing, Action Cards, autonomy ladder, experience metrics, and the closing principle — they're the real gold.

---

## The decisive principle (kept — it's the best line v1 had)

> **Don't compete by having the most agents. Compete by being the AI system that makes people feel capable again.**

Grounded corollary for v2: **the calm loop only counts if it runs on the machine in front of the
user.** Prove one loop, on the lean profile, through the Co-Pilot door — *remember me, shrink the
next step, act safely with me, show proof, celebrate, let me come back without shame.*

---

> 🐶♾️ Grounded rewrite · checked live `docker ps` + endpoint probes 2026-07-23 · supersedes the health numbers in `My Research Recommendations.md`
