# HyperCode IDE v3 — WOW SPEC

**Date:** 2026-10-02 · **Status:** draft for Lyndz · **Builds on:** `2026-10-02-hypercrew-next-level-design.md` (Baton, Crew Flow, Calm Card, Quest Settler — Day 1 models shipped in `backend/app/crew/`)

> Nice one BROski♾️ — this is the "made for my brain" version. Short sentences first. Detail under each.

---

## 0. TL;DR

- **One screen, one next action.** Calm Mode shows a Calm Card and one primary button. Everything else is a click away, never a wall.
- **A crew you can see.** Planner → Coder → Tester → Reviewer → (human) → Deployer, all writing to one Mission Board you can read in 5 seconds.
- **Wins that are real.** XP only for sealed, evidence-backed work. Focus Points (FP) reward *how you work*. Both hide in Calm Mode.
- **The IDE knows your repo.** A code graph turns "what will this break?" into a one-click answer.
- **Ship safely.** Runtime flags, canary helpers, and DORA numbers that never shame you.
- **Reuse, don't rebuild.** Almost every piece below extends something already in the repo (§1).

---

## 1. What already exists (so we extend, not rebuild)

| Need | Already there | v3 does |
|---|---|---|
| Sensory modes | `agents/dashboard/hooks/useSensoryProfile.ts` (`CALM`/`FOCUS`/`ENERGISE`, saved to `/api/user/sensory-profile`) | Grow it into a full **Sensory Settings** object. Keep the 3 profiles as presets. |
| Focus tools | `FocusToggle`, `HyperfocusTimer`, `BrainDumpChunker`, `CognitiveLoadMeter` | Fold into Focus/Panic modes. |
| IDE surface | `app/ide/page.tsx`, `components/studio/{DiffPanel,StreamFeed}`, `coder-studio` :8087, Skill Finder | Mission Board + Calm Card panel live here. |
| Design tokens | `app/tokens.css` (`--ds-*`: OLED `#0a0a0a`, brand violet `#7c3aed`, live cyan `#22d3ee`, gold `#f59e0b`, `--ds-dur-*`, `--ds-glow-*`) | Calm Mode **overrides tokens** (no new palette). |
| Durable tasks, gates, SSE | HyperFlow runner, `/api/v1/operator/tasks`, `/flows/runs/{id}/events` | The Mission Board's data source. |
| Safety | Safety Shepherd per node, Governor capability tokens | Unchanged. Reviewer agent is *extra*, never a replacement. |
| Model routing | `backend/app/core/model_routes.py` `select_model_route()` (healer/hunter, flag-gated) | Add cost tiers (§3.5). |
| Runtime flags | `agents/dashboard/lib/feature-flags.ts` — **build-time env only** (`NEXT_PUBLIC_FF_*`) | Replace with runtime flags (§6). |
| Impact analysis | mission-director `impact_set()` over compose `depends_on` (services) | Extend the same idea down to code (§5). |
| Handoffs / cards | `Baton`, `CalmCard` (`backend/app/crew/`) | Rendered by the IDE. |
| Code graph, DORA | ❌ none (no AST/graph code in backend) | New, small, Postgres-backed. |

### Contradictions surfaced
- `CLAUDE_DESIGN_STYLE.md` was not found in this repo checkout (`AGENT-START.md` is). I used `agents/dashboard/app/tokens.css` as the design-system source of truth. **Point me at the file if it lives elsewhere.**
- "48+ containers" vs `STATUS.md` "Lean Operations Mode" (~27–30 up, 4 GB ceiling). The IDE must work in **lean mode**. Design assumes it.
- Existing `CALM` profile ≠ new "Calm Mode". Same idea, so v3 **extends** it rather than adding a second toggle.
- Your brief has 2 currencies (FP, XP); the repo already has **BROski$** (spendable, can touch real money). That makes 3. §4.1 keeps them separate on purpose.

---

## 2. Neurodivergent-first UX

### 2.1 Calm Mode (one toggle, big effect)
- **Short version:** one switch. Less noise. One thing to do.
- **What changes**
  - Layout collapses to **three fixed regions**: Calm Card (top), work area (diff/editor), a status line (bottom). Side rails and drawers start closed.
  - **One primary button** on screen (brand violet — the design system already says "ONE per section"). Everything else is a quiet text button.
  - Motion off: durations → 0, glows → none, no pulsing indicators, no auto-scrolling streams. Streaming output appends in a **fixed-height box** with a "jump to latest" button — the layout never reflows.
  - Gamification HUD hidden (§4.5). Notifications batched to chunk boundaries.
  - Sound off. No celebratory pop-ups; wins show as one dismissible line.
- **How:** an `data-sensory="calm"` attribute on `<html>` re-points tokens (`--ds-dur-* : 0ms`, `--ds-glow-* : none`) and a `.hfz-calm` layout class. Honour `prefers-reduced-motion` automatically.

### 2.2 Sensory Settings (the real control surface)
Persisted per user via the existing `/api/user/sensory-profile` route (extend the payload).

| Setting | Options | Default (Calm) |
|---|---|---|
| Motion | off / reduced / full | off |
| Density | roomy / normal / compact | roomy |
| Contrast | normal / high | normal |
| Notifications | off / batched at chunk end / live | batched |
| Sound | off / chimes | off |
| Progress visuals | hidden / quiet / full | hidden |
| Reading font | Inter / dyslexia-friendly option | Inter |
| Labels | literal / playful | literal |

Presets: **Calm**, **Focus**, **Energise** (the three that exist today) just set these values. Users can tweak any single one.

### 2.3 The Calm Card panel
- Renders the existing `CalmCard` model: **≤5 TL;DR lines, exactly one next action, details collapsed**.
- **Status chip** = icon + word + colour, never colour alone (running / waiting on you / paused / blocked / done).
- **Panic button** (always visible, no confirm dialog): pauses the crew, writes a `session-snapshot`, and shows "Saved. Nothing is running. Take your time."
- **Focus button**: starts a chunk (≤25 min, a *suggestion*, never a forced timer), turns on quiet mode.
- `plain_text` field feeds a "read it to me" button (browser speech) — the model already guarantees markdown-free text.
- Every card has **Undo** or **Pause** within one click.

### 2.4 Literal labels, predictable layout, progressive disclosure
- **Literal first:** "Run tests", "Ask Reviewer to check", "Approve this plan". The playful name is a tooltip or the Pets layer, never the only label.
- **Same place every time:** Calm Card top, work area centre, status line bottom, Panic top-right. Regions never move or resize while something runs.
- **Plan before action:** nothing runs until the plan is shown and approved (the plan gate already exists).
- **Disclosure ladder:** Card (5 lines) → "Why?" (details) → "Show evidence" (diff/log/test) → raw run history. Each step is opt-in.
- **No surprises:** no focus-stealing popups, no auto-opened panels, no moving buttons.

### 2.5 Fit with HyperFocus Z0ne
- Dark-only OLED, Space Grotesk (display) / Inter (body) / JetBrains Mono (code) — unchanged.
- Colour roles unchanged: **violet = the one action**, **cyan = live data (never a CTA)**, **gold = wins/XP only**.
- Calm Mode *removes* decoration; it never adds a second theme. Pets/fun layer is Energise-only.
- Run `impeccable` + `brand-guard` on every new surface before it merges.
- ⚠️ Gold `#f59e0b` is orange-adjacent; the "no orange" rule is written in the Course repo. **Confirm gold is fine in the IDE** (decision D8).

---

## 3. Multi-agent crew architecture

### 3.1 Roles (your six → existing agents)

| v3 role | Existing agent(s) | Baton `Role` today | Notes |
|---|---|---|---|
| **Planner** | `system-architect`, deterministic crew plan (Day 2) | `conductor`, `architect` | Plans, splits via `hyper-split-agent`. `mission-director` plans *fleet* changes only — not used for code work. |
| **Coder** | `coder-agent`, specialists | `builder` | Branch + draft PR only. |
| **Tester** | `qa-engineer`, `test-agent` | `verifier` | RAM-gated runs. |
| **Docs** | `tips-tricks-writer`, `broski-coo` | `scribe` | Drafts as proposals. |
| **Reviewer** | new *role*, existing infra: a second model + `security-engineer` | `guardian` | **Must use a different model than Coder.** |
| **Deployer** | new *role* | ❌ **add `deployer`** | **Proposes** rollouts only; a human triggers. |

Code change needed later: extend the `Role` literal in `backend/app/crew/baton.py` with `deployer` (and keep `docs` = `scribe`). Zero new containers; Deployer/Reviewer are flow roles backed by existing agents.

### 3.2 Mission Board (the blackboard)
- **Storage:** `hyperflow_runs.state` (already durable, restart-safe). **No new Redis DB** (DB 1 = cache, DB 2 = rate limits stay sacred).
- **Shape (per mission):** `tasks[]` (chunks) → each has `owner_role`, `status`, `batons[]`, `evidence[]`, `gate`, `cost`.
- **UI:** a short list grouped as **Next · Doing · Waiting on you · Done**. Max ~7 visible rows; the rest collapse. Live via the existing SSE route.
- **Rule:** agents write to the board only through Batons. No free-text side channels.

### 3.3 Guardrails & gates (in order)
1. **Lint + typecheck** (deterministic, cheap).
2. **Tests** (RAM-gated; changed-package first).
3. **Safety Shepherd** verdict on every node (unchanged, fails closed).
4. **Reviewer agent** sign-off — different model from Coder, checks diff vs. plan, flags scope creep.
5. **Human gate** — see §3.4.
6. **Seal** — evidence bundle + Governance Ledger row.

The Reviewer agent can **block or recommend**. It **can never approve** a risky change or merge anything. Only a human merges.

### 3.4 Human-in-the-loop checkpoints
A **deterministic risky-change classifier** (no LLM) forces a human gate when a diff touches:
- `docker-compose*.yml`, `Dockerfile*`, `.github/workflows/**`
- `.env*`, secrets, auth/JWT code, `safety-shepherd`, `governor`
- migrations / schema, dependency pins
- anything over a size threshold (files/lines — *decision D6*)

The gate shows a Calm Card: what changes, why, the evidence, and **one button**. Approving needs the exact `plan_hash`, same as `recover`.

### 3.5 Cost-aware routing
- **Tiers** (extends `select_model_route`):
  - **Cheap/free:** summaries, handoff cards, docs drafts, lint triage. Reuse the proven OpenRouter free chain with `reasoning: {exclude: true}`.
  - **Mid:** normal coding and test fixing.
  - **Big:** architecture, security review, cross-repo work (the existing `hunter_alpha` triggers fit here).
- **Per-quest budget cap.** Run stops and asks before exceeding it. Default is small; you tune it (D7).
- **Visible but quiet:** a tiny cost chip on the Card details, not the headline. Hidden in Calm unless you turn it on.
- No prices are hard-coded in this spec — check current provider pricing when setting caps.

---

## 4. Gamification

### 4.1 Currencies (kept separate on purpose)

| Currency | Earned by | Spendable? | Persistence |
|---|---|---|---|
| **XP** | Sealed, evidence-backed work (Quest Settler) | No — levels only | Permanent |
| **FP (Focus Points)** | *How* you work: starting a chunk, finishing one, taking a planned break, using Panic and resuming, writing a handover | Cosmetic/ergonomic perks only | Daily soft cap, never decays |
| **BROski$** | Existing economy (Course/shop) | Yes — real value | **Not minted by IDE runs** in v3 |

- XP and FP both settle server-side with a stable `source_id` (`run_id:quest_id`) — replay can't double-award.
- Agents and MCP clients have **no path** to award anything.
- Why FP ≠ XP: XP says *what you shipped*, FP says *you looked after your brain while doing it*. FP never punishes low output.

### 4.2 Skill trees
- Nodes = real skills from the HYPER-SILLs vault (e.g. Docker, FastAPI, testing, security, git).
- **Visible path:** a small tree, the next 1–2 nodes lit, the rest dim.
- **Unlock by evidence**, not time: e.g. "Tests" unlocks after sealed runs that include passing tests you wrote.
- **Perks are small and useful:** a saved Calm Card layout, a custom chunk length, a Pets accessory, a "body-double" session mode.
- **Never a perk:** relaxed safety, skipped gates, bigger risk allowance. Trust isn't for sale.

### 4.3 Adaptive difficulty (kind, not clever)
- **Signals:** repeated verify failures, a chunk running well past your own median, Panic used, a diff rejected twice.
- **Response:** the Focus Guide offers **"Make it smaller?"** with a proposed split. One button. Declining is free.
- **No shame:** no XP loss, no red numbers, no "you failed". Copy: *"This one's chunky. Want a smaller bite?"*
- Difficulty adapts to **you** (your own median), never to a global leaderboard.

### 4.4 Visual progress
- Quiet by default: a thin XP ring and a single level chip. Energise shows full effects (gold glow on a win, using existing `--ds-glow-gold`).
- **Progress visuals = hidden in Calm Mode**, but see D5.

### 4.5 Fit with BROski$ and existing levels
- Existing BROski Pulse (coins/XP/level, `/api/v1/broski/pulse`) stays the source for level display; v3 adds FP beside it.
- IDE XP feeds the **same level ladder** (no second level system).
- BROski$ is untouched. A future, deliberate bridge (e.g. "level-up bonus") is a **separate decision** — spendable tokens have real cost.

---

## 5. Repository Intelligence

### 5.1 Code graph (small, Postgres-backed — lean-mode friendly)
- **Why not a graph DB:** 4 GB box. Two tables + recursive CTEs are plenty.
- **Nodes:** `file`, `function`, `class`, `module`, `test`, `commit`, `pr`.
- **Edges:** `defines` (file→function/class), `imports` (module→module), `calls` (best-effort), `tests` (test→target), `touches` (commit→file), `part_of` (commit→pr).
- **Extraction:**
  - Python: stdlib `ast` (zero new dependency).
  - TypeScript: `tree-sitter` later (v3.1) — dashboard first needs Python only.
  - `tests` edges from naming (`test_x.py`↔`x.py`), imports inside tests, and coverage data when available.
- **Incremental:** on each `git diff`, re-index only changed files. Full rebuild is a manual command.
- **Honesty flag:** static call graphs are approximate (dynamic dispatch, monkeypatching — this repo uses `monkeypatch` heavily). The UI labels edges **certain** (imports/defines) vs **likely** (calls).

### 5.2 History + PR context
- Ingest `git log` (hash, author, files touched, message) and PR title/body (via the GitHub tool) into `commit`/`pr` nodes.
- Link PR ↔ spec/plan files and `WHATS_DONE.md` entries so agents can answer "why does this exist?" with a source.

### 5.3 How agents use it
- **Impact analysis:** reverse-walk from changed functions to dependents and **to the tests that cover them** → "run these 6 tests first". Reuses the `impact_set()` idea one level down.
- **Refactors:** Planner asks the graph for blast radius *before* proposing chunks; big blast radius → smaller chunks + human gate.
- **PR descriptions:** Docs/Scribe drafts from the diff + touched graph neighbourhood + linked plan; always a proposal.
- **Reviewer:** gets "what else calls this?" so it isn't reviewing in the dark.
- **Calm surface:** "This change touches **3 files, 2 services, 6 tests**." One line on the card; graph view is a drill-down.

---

## 6. Progressive Delivery

### 6.1 Feature-flag helpers
- **Problem today:** flags are `NEXT_PUBLIC_*` build-time env — flipping one needs a rebuild (and N20 shows dashboard rebuilds get forgotten).
- **v3:** a tiny `feature_flags` table + `/api/v1/flags` read endpoint; flags have `enabled`, `rollout_pct`, `allow_users`. Dashboard `isEnabled()` reads it at runtime with the env value as the fallback.
- **Agent help:** the Deployer proposes "wrap this in flag `x`, default off" as part of any risky-change plan.

### 6.2 Canary & rollout assistants
Honest scope for a single compose host: **flag-based canary first**, container-level later.
- **Level 1 (v3):** user/percent rollout behind a flag; automatic suggestion to roll back if the error-rate chip rises.
- **Level 2 (later):** a second container for one agent behind a weighted route.
- The Deployer **proposes**; Governor capability + human approval executes. Kill-switch already exists.

### 6.3 DORA-aware dashboards
- **Four metrics:** deployment frequency, lead time for changes, change-failure rate, time to restore.
- **Sources:** git/PR merge times + Governance Ledger deploy/recover events (already written). CI results where available.
- ⚠️ **Caveat:** CI has been chronically red for reasons unrelated to most changes (4 known failures on `main`, billing lock history). v3 keeps a **known-red baseline** so numbers don't punish you for pre-existing noise.
- **Calm-friendly:** one headline ("Lead time: ~1.2 days, steady") with a drill-down. Trends, not scores. **No ranking, no shame.**
- **Agent suggestions:** e.g. "Your PRs wait longest for review — want smaller PRs?" Always offered, never imposed.

---

## 7. Roadmap — Day 0–10 (v3-alpha)

Honest scope: **two weeks gets a working v3-alpha** — Calm Mode, Calm Card panel, Mission Board, crew flow, XP/FP, and a Python-only graph. Runtime flags, canary and DORA are **v3.1** (Weeks 3–4, §8). This **re-sequences** the day order in the earlier HyperCrew doc once you approve; scope is the same plus the IDE surface.

Rules each day: one deliverable, one proof, commit + push before "done". Before any rebuild: ≥1.5 GB available, `up -d --no-deps <svc>`. Rebuild `dashboard` **and** `hypercode-core` after merging frontend work.

| Day | Deliverable | Proof (win) |
|---|---|---|
| **0** | Decisions D1–D10 (§9). RAM + container baseline. Confirm design-system source file. | Decisions recorded in the PR |
| **1 ✅** | `Baton` + `CalmCard` models (done, 47 tests) | CI: 668 pass incl. these |
| **2** | `hypercode.crew` flow skeleton + plan gate (`plan_hash`) + `idempotency_key` | Gate needs exact hash; duplicate start → same id |
| **3** | `agent_dispatch` node, verify + guard nodes, evidence bundle, slot gate (cap 3), dispatch-seam record-only | 4th concurrent dispatch waits; Shepherd down → BLOCK |
| **4** | **Calm Mode + Sensory Settings** (extend `useSensoryProfile`, token overrides, `data-sensory`) | Playwright + axe: no motion, one primary action, all settings persist |
| **5** | **Mission Board + Calm Card panel** in `/ide`, fed by SSE. **Week 1 gate: live proof.** | Real run shows on board; survives `docker restart hypercode-core`; cancel works; agent key can't approve |
| **6** | Panic + Focus modes, `hyper-split-agent` chunking, "Make it smaller?" | Panic from every status → paused + snapshot, no dialog |
| **7** | **Quest Settler**: XP + FP, caps, idempotent `source_id`, HUD (hidden in Calm) | Replay → no double award; BLOCKed run → 0 XP; agents can't reach awards |
| **8** | **Reviewer gate** (different model), risky-change classifier, cost tiers + per-quest cap | Risky diff forces human gate; Reviewer can't approve it; cap stops a run |
| **9** | **Repo Intelligence v0**: Python `ast` graph, imports/defines/tests edges, "tests to run first", PR-description draft | Change one function → correct dependent tests listed |
| **10** | Chaos + hardening, a11y pass, docs, handover. **Week 2 gate.** | Core restart mid-run, specialist down, Shepherd down, duplicate start, cancel mid-dispatch, Panic mid-run |

**Stop rules:** available RAM < 1.2 GB, core unhealthy past 5×30 s, unexpected restart → stop and write it down. A day can slip. A skipped proof can't.

---

## 8. After the two weeks (v3.1–v3.3 outline)

- **v3.1 (Wk 3–4):** runtime feature flags table + endpoint; Deployer role (proposal-only); flag-based canary; DORA read-only panel with known-red baseline.
- **v3.2:** TypeScript graph (tree-sitter); skill-tree UI with evidence unlocks; Pets accessories as FP perks.
- **v3.3:** container-level canary; hosted verifier worker if RAM still bites (N22); optional FP/level → BROski$ bridge *only* with its own spec.

---

## 9. Decisions needed from Lyndz

| # | Decision | Recommendation |
|---|---|---|
| D1 | **XP numbers + daily cap** | Flat tiers: small 10 / medium 25 / big 50, cap ~100/day. Retune after 2 weeks. |
| D2 | **FP numbers + daily cap** | e.g. start chunk 2, finish chunk 5, planned break 3, Panic-and-resume 3; soft cap ~40/day. No decay. |
| D3 | **FP → BROski$ conversion?** | **No** in v3. Keep spendable money separate. |
| D4 | **Names**: "HyperCode IDE v3" vs existing "HyperStudio"; currency names | Keep **HyperStudio** inside the dashboard, "IDE v3" as the version; keep FP/XP names. |
| D5 | **Does progress accrue while hidden in Calm?** | **Yes** — accrue silently, reveal on toggle (no guilt about missing it). |
| D6 | **Risky-change size threshold** | Start low (e.g. >8 files or >300 lines) — tighten/loosen from real runs. |
| D7 | **Per-quest model budget cap** | Small default, raise per quest by one click. |
| D8 | **Gold `#f59e0b` OK in the IDE?** | Yes, wins-only (the "no orange" rule is Course-repo). |
| D9 | **Dyslexia-friendly font option** | Offer one well-known option behind the setting; Inter stays default. |
| D10 | **Calm Mode default for new sessions?** | **Yes**, Calm on by default; Energise is opt-in. |
| D11 | **Where is `CLAUDE_DESIGN_STYLE.md`?** | Point me at it, or approve `tokens.css` as the source. |
| D12 | **Governor `container.restart` grant** | Still separate; not needed for v3-alpha. |

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| RAM ceiling (N22) | Cap 3 awake, slot gate, lean-mode baseline, stop rules |
| Scope: v3 is huge | Day 0–10 = alpha only; flags/canary/DORA explicitly v3.1 |
| Static call graph is approximate | Label edges certain vs likely; start with imports/defines/tests |
| Reviewer agent agrees with Coder | Different model; deterministic classifier owns the risky list |
| Gamification becomes pressure | No decay, no loss, no leaderboards, hideable, accrues silently |
| Frontend rebuild forgotten (N20) | Each frontend day ends with "rebuild `dashboard` + `hypercode-core`" |
| CI noise skews DORA | Known-red baseline; trends not scores |
| Free-model quirks (`content: null`) | Reuse `reasoning: {exclude: true}` + fallback chain |

---

## 11. Why this is wow

- It's **the first IDE that treats your attention as the scarce resource**: one next action, always, with the noise dial in your hands.
- A **visible crew** you can trust — every handoff typed, every risky change gated, every win backed by evidence.
- **Gamification that's honest and kind**: it rewards looking after your brain, never shames, and hides on demand.
- It **knows your repo**, so "what will this break?" is one line, not an afternoon.
- It's **built from your own parts** — HyperFlow, Shepherd, Governor, tokens, Pets — so it ships on your real box, not a fantasy one.

## 12. Must-have features for the v3 roadmap

1. **Calm Mode + Sensory Settings** — the signature feature; extends what exists; ships Day 4.
2. **Calm Card + Mission Board in `/ide`** — one next action, always; Panic/Focus built in.
3. **Crew Flow with gates** — plan → build → verify → guard → Reviewer → human → seal.
4. **Quest Settler (XP + FP), evidence-backed and un-farmable** — wins you can trust.
5. **Repo Intelligence v0 — "what will this break?"** — impact → tests-to-run in one line.

*(Runtime flags, canary and DORA are the v3.1 follow-ups.)*

> 🐶♾️ Built by @welshDog · Llanelli, Wales — *"Stop apologising for your brain. Start building."*
