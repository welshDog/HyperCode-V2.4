# 🧬 HYPERCODE V3 — Hyper AGI Auto Agents

> **The world's first neurodivergent-first autonomous AI infrastructure platform**
> **Version**: V3.0 (Hyper AGI) — grounded rewrite
> **Status**: Blueprint — August 2026, rewritten 2026-08-21
> **Built by**: @welshDog + BROski swarm ⚡

---

## ⚠️ What Changed (2026-08-21) — read this first

The previous version of this file proposed replacing HyperCode's orchestration
with LangGraph + A2A protocol + a multi-provider LLM router (Grok 4.5, Kimi
K3) + Pydantic AI 2.0 memory, over an 8-sprint migration. Before starting
that work, three parallel repo audits checked its claims against the real
codebase. Every one of them came back wrong:

1. **Wrong target repo.** The doc frames V3 as `HyperCode-V2.4` "evolving"
   via `THE-HYPERCODE`. `THE-HYPERCODE` is a real, separate repo — but its
   own README describes it as *"HyperCode: Programming Language for
   Neurodivergent Brains"* (multi-paradigm, MLIR-based IR). It is not an
   agent-swarm platform, has zero LangGraph/A2A/Pydantic-AI code, and its
   last commit predates this roadmap by over a month.
2. **Phantom sibling docs.** `HYPERCODE_V3_MIGRATION.md`, `_API.md`,
   `_NEURO.md`, `_EXAMPLES.md` were all listed as part of this plan.
   None exist anywhere in the workspace.
3. **Fabricated example.** The "legacy" `manifest.json` this doc cited
   (`{"agents": ["planner","coder","reviewer"], "orchestration": "sequential"}`)
   doesn't match `HyperAgent-SDK`'s real schema — a single-agent descriptor,
   not a swarm list.
4. **Zero prior art for the proposed stack.** Real repo-wide checks:
   LangGraph — one hand-rolled "LangGraph-*style*" file, not the real
   package, unused anywhere. A2A — a single `a2a: bool = False` field whose
   own code comment reads *"nothing implements A2A yet."* Pydantic AI —
   pinned in a requirements file the Dockerfile doesn't even install from;
   zero imports anywhere in `backend/`. Grok / Kimi — zero references
   anywhere in this codebase except the old draft of this file.
5. **It ignored the safety architecture this repo already built and
   proved.** `agents/fleet-controller/` (Phase 0, shipped 2026-08-20/21)
   enforces a governing rule — **no component may both interpret LLM
   output and possess infrastructure mutation authority** — via a
   fail-closed, zero-mutation-authority design, 26 passing tests, and a
   live smoke test proving a Safety Shepherd outage correctly `BLOCK`s
   rather than fails open. Safety Shepherd (ALLOW/BLOCK/ESCALATE, explicit
   capability grants required for `DANGEROUS` categories) and the
   Governance Ledger (full audit trail) are both live. HyperFlow's own
   design doc *already explicitly rejected* an LLM-driven graph compiler
   for v1: *"disproportionate risk for the current flow count... a
   generated graph would get none [review]."* The old draft's "agents that
   plan, code, test, deploy, and learn without human intervention" pitch
   reintroduced exactly the risk pattern this repo already identified and
   turned down once.

**What's actually true and worth building on**: specialist agents
(`agents/*/base_agent.py`) already make real `AsyncAnthropic` calls to do
real task work (default `claude-sonnet-4-6`) — this is not a stub fleet.
`agents/crew-orchestrator/crew_v2.py` is a genuine CrewAI hierarchical LLM
planner with an Opus/Sonnet/Haiku tier map — real code, just dead: never
imported by the live dispatch path (`main.py`), which is deliberately
deterministic HTTP routing, not agentic planning.

This rewrite keeps the "V3 / Hyper AGI" ambition but builds it on what's
real: the mission-director path the fleet-controller Phase 0 spec already
points at, not a framework swap with no containment design.

---

## 🎯 Executive Summary

HyperCode V3 does not replace the orchestration layer. It extends the
safety-first path already in motion — `fleet-controller` Phase 0 proved a
containment boundary can exist; V3 adds the LLM planner in front of it,
under one rule that must hold at every phase:

> **No component may both interpret LLM output and possess infrastructure
> mutation authority.**

Autonomy grows by adding phases behind that boundary — a typed plan
proposer, capability tokens, a gated human-approval step, then (only once
all of that is proven) bounded live execution — not by giving an LLM a
bigger blast radius up front.

---

## 🧠 V3 Architecture — the real pipeline

```
┌───────────────────────────────────────────────────────────────────┐
│                     HYPERCODE V3 — MISSION PIPELINE                 │
├───────────────────────────────────────────────────────────────────┤
│                                                                       │
│  brain-agent          capability recommendation                     │
│      │                (what's possible, given current world model)  │
│      ▼                                                               │
│  mission-director     typed plan proposal                            │
│      │                LLM-driven. Zero mutation authority — cannot   │
│      │                touch Docker, credentials, or infra directly.  │
│      ▼                                                               │
│  fleet-controller     DRY_RUN / policy check                         │
│      │                Zero LLM client. Deterministic validation only.│
│      │                (live today — Phase 0, see below)              │
│      ▼                                                               │
│  Safety Shepherd      ALLOW / BLOCK / ESCALATE verdict                │
│      │                (live today)                                   │
│      ▼                                                               │
│  Governance Ledger    evidence, full audit trail                     │
│      │                (live today)                                   │
│      ▼                                                               │
│  human review         approve / reject / revoke / replan             │
│      │                dashboard                                      │
│      ▼                                                               │
│  [later phase, gated] bounded live execution                         │
│                                                                       │
│  mission evaluator ── watches every run above, compares intended vs. │
│                        actual outcome, safety events, cost, human     │
│                        corrections, rollback quality → structured     │
│                        lessons. Not a second executor.                │
│                                                                       │
│  truth registry ────── feeds mission-director a trustworthy world     │
│                        model (real compose facts + a thin, self-      │
│                        validating overlay) so it never plans against  │
│                        stale docs. Spec: see below.                   │
│                                                                       │
└───────────────────────────────────────────────────────────────────┘
```

This is the same pipeline named in the fleet-controller Phase 0 spec's
future-phases section, plus a mission evaluator and truth registry — both
proposed in a 2026-08-21 review of the Phase 0 work
(`HyperCode-V2.4/AGI-infrastructure upgrade`, local, uncommitted).

---

## ✅ What's Already Real — Don't Rebuild It

| Piece | State | Where |
|---|---|---|
| Specialist agents making real LLM calls | ✅ Live | `agents/*/base_agent.py` — `AsyncAnthropic`, default `claude-sonnet-4-6`, Ollama fallback |
| A hierarchical LLM planner (candidate mission-director seed) | 🟡 Written, dead code | `agents/crew-orchestrator/crew_v2.py` — CrewAI, tier-mapped Opus/Sonnet/Haiku, never imported by `main.py`. Phase 1 must explicitly decide: adopt as the seed, or retire it — leaving it live-but-unwired is its own drift risk. |
| Containment boundary (fail-closed, zero mutation authority) | ✅ Live, smoke-tested | `agents/fleet-controller/` — `plan_validator.py`, `safety_client.py`, `models.py`. 26 tests. |
| ALLOW/BLOCK/ESCALATE policy engine | ✅ Live | `agents/safety-shepherd/policy.py` — `DANGEROUS` categories require explicit capability grants |
| Audit trail | ✅ Live | Governance Ledger — `backend/app/api/v1/endpoints/governance.py` |
| Deterministic mission graphs | ✅ Live | HyperFlow (`backend/app/agents/hyperflow/`) — goal-matcher, not a graph generator. Its own design doc already rejected LLM-driven graph compilation for v1; mission-director must route through its own validated-plan boundary, not bypass HyperFlow's existing caution. |
| Fleet truth model | 🟡 Spec'd, not built | `docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md` |

---

## 🗺️ Phased Roadmap

- **Phase 0 — fleet-controller**: ✅ done (2026-08-20/21). Containment
  boundary proven: fail-closed, zero LLM client, zero mutation authority,
  live smoke test (Shepherd killed mid-request → `BLOCK`, denied profile →
  `422` before Shepherd is ever contacted).
- **Phase 0.5 — truth registry**: 🟡 spec'd 2026-08-21
  (`docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`), not
  yet implemented. Prerequisite for mission-director — a planner fed stale
  docs makes bad plans.
- **Phase 1 — mission-director**: typed plan proposal, LLM-driven, zero
  mutation authority (same governing rule as Phase 0). Resolve
  `crew_v2.py`'s fate as part of this phase — adopt its tier-mapped
  planning approach or retire it, don't leave it ambiguously dead.
- **Phase 2 — capability tokens**: signed verdicts, matching the reserved-
  but-unset `PlanResponse.capability` field already in `fleet-controller`'s
  models.
- **Phase 3 — human approval gate + first live action**: two-person-rule
  for the DRY_RUN→LIVE switch, exactly as the Phase 0 spec already commits
  to.
- **Phase 4 — mission evaluator**: intended vs. actual outcome, safety
  events, cost, corrections, rollback quality → structured lessons.
- **Phase 5 (only after 0–4 are proven)** — incremental LLM-capability
  improvements: e.g. extending `crew_v2.py`'s existing tier map for
  cost/quality routing across tasks. Evaluated case-by-case with real
  evidence once there's a live system generating it, not adopted upfront as
  speculative architecture.

Each phase ships independently and is smoke-tested against the live stack
before the next one starts — the same discipline Phase 0 already used.

---

## 🧠 Neurodivergent-First Agent UX

Unchanged in spirit from the original draft — none of this conflicts with
anything real, and it extends the existing Flow Keeper pattern.

#### Interrupt-Safe State
Hyperfocus sessions should be able to pause and resume without losing
mission context. Once mission-director (Phase 1) has a real session/state
model, hook checkpointing into *that* — this is deliberately not tied to
LangGraph, since LangGraph isn't part of this roadmap.

#### Chunked Output Contracts
```yaml
output_format:
  max_sentences_per_response: 3
  structure:
    - summary: 1 sentence
    - details: optional, expand on request
    - next_action: 1 sentence
  style: "short-burst, bullet points, no walls of text"
```

#### Momentum Agents (BROski$ Micro-Rewards)
Mission evaluator (Phase 4) is the natural trigger point — a completed,
evaluated mission step fires a reward, not raw task completion, so rewards
track real progress rather than busywork.

---

## ❌ Explicitly Dropped — and why

| Dropped | Why |
|---|---|
| LangGraph | Zero prior art in this codebase (one unused hand-rolled stand-in). Would replace a live, proven orchestration layer — a profile-dependent Docker platform with 20+ compose files and a large service fleet — for no demonstrated need. |
| A2A protocol | A single unset placeholder field exists; nothing implements it. No external agent (Copilot/Cursor/Devin) integration is currently needed. |
| Pydantic AI 2.0 memory migration | Pinned in an unused requirements file, zero real usage. `Configuration_Kit`/context-key memory already works. |
| Multi-provider router (Grok 4.5, Kimi K3) | Zero references anywhere in this codebase before the original draft. `crew_v2.py` already has a tier-mapping pattern (Opus/Sonnet/Haiku) — extend that later with real cost evidence if needed, rather than adopting untested providers upfront. |
| External agent integration (A2A to Copilot/Cursor/Devin) | No current use case; revisit only if a real cross-system workflow needs it. |

None of these are required to reach the containment-first version of
"Hyper AGI Auto Agents." Any could be reconsidered later as a narrow,
evidence-driven decision — never adopted as upfront speculative
architecture again.

---

## 📊 Success Metrics

Replaces the old vibes-based "80% fully autonomous" target with concrete,
testable categories (from the 2026-08-21 Phase 0 review):

| Category | What it tests |
|---|---|
| **Mission generality** | Can the system handle a new feature, a failing container, a DB design task, a security incident, a doc contradiction, a cross-repo dependency change? |
| **Long-horizon persistence** | Can it resume a mission after a service restart, a model switch, a partial failure, a human rejection, a queue delay? |
| **Correctability** | Can Bro pause the mission, revoke its authority, reject one action, change the goal, force a replan, recover from a bad plan? |
| **Containment** | Can a compromised planner create no Docker mutation, obtain no execution credential, bypass no policy, alter no audit record, escalate no scope? |
| **Evidence quality** | For every decision: what was known, what was proposed, which model proposed it, which policy evaluated it, what was approved, what actually happened? |

---

## 🎯 Next Steps (Immediate)

Scope mission-director Phase 1 via the brainstorming skill — same rigor as
the fleet-controller Phase 0 spec (context/constraints → goal → design
sections → written spec → self-review → implementation plan).

---

## 🚀 V3 Vision Statement

> **HyperCode V3 is not just an upgrade — it's proof that increasing
> autonomy and hard containment aren't in tension.**
> HyperCode-V2.4 is a profile-dependent Docker platform with 20+ compose
> files and a large service fleet; V3 extends its **agent-control plane**
> rather than replacing its container foundation. Where V2.4 orchestrates
> containers, V3 orchestrates **bounded autonomous
> intelligence** — agents that propose, get checked, get approved, and
> only then act, while preserving the hyperfocus flows that make BROski
> brains unstoppable.
> **The safest foundation first. Then everything else.** ⚡♾️

---

**Built by**: @welshDog + BROski swarm
**Location**: Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥
**Date**: August 21, 2026 (rewritten)
**Version**: V3.0 Blueprint (grounded rewrite)

*"Stop apologising for your brain. Start building."* 🐶♾️
