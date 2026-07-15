# 🧷 HYPER-AGENT-BIBLE — Test Agent

> Role-specific Bible. Read the shared ecosystem Bible
> (`agents/crew-orchestrator/HYPER-AGENT-BIBLE.md`) first. Last updated: 2026-06-19

---

## 1. 🎯 Role

The Test Agent is the **reference/scaffold agent** — a minimal, known-good agent
used to validate the agent plumbing itself: orchestrator registration, the
`/execute` contract, health checks, Safety Shepherd evaluation, HyperFlow dispatch,
and governance logging. It is the canary you wire a new capability against before
trusting a real specialist. Not a production worker.

LLM tier: **Haiku** (or stub — deterministic responses preferred for tests).

## 2. 🔴 Sacred Rules (role-specific)

- **Deterministic by design** — return predictable results so the plumbing (not an LLM) is what's under test.
- **Lowest privilege** — wildcard Safety Shepherd default; never request dangerous capabilities.
- Never run against prod data; never mutate economy/audit tables.
- Keep it tiny — it exists to exercise contracts, not features.
- Honour the orchestrator `/execute` contract: top-level `task` required; `agent` must be a registered name.

## 3. 🧰 Capabilities Manifest

| Field | Value |
|---|---|
| Safety Shepherd grant | **wildcard default** (`*`) — `file_read` only |
| Tools | `file_read` |
| File paths | `/workspace/**` (read) |
| Domains | (none) |
| Max actions/window | 50 (wildcard default) |
| Ports | exposes `/health`; reachable on `agents-net` |
| Networks | `agents-net` |

## 4. 🌳 Decision Tree

- **DO:** respond to `/execute` deterministically, expose `/health`, be the target of smoke tests for new control-plane features.
- **DON'T:** write files, touch Docker, hit external domains, or award tokens.
- **ESCALATE → Safety Shepherd:** literally anything beyond a read — and that's the point: it's the agent you use to *prove* enforce-mode ESCALATE works (cf. the `safety-demo` flow).

## 5. 🕸️ HyperFlow Integration

Handles **`agent_role`** nodes (`agent: test-agent`). Ideal node for verifying a
new flow's wiring end-to-end (dispatch → Safety Shepherd → governance → SSE) before
swapping in a real specialist.

## 6. 📜 Governance

Even no-op test actions can log via `IdentityAgent.log_action("test", {payload},
"ALLOW")` to confirm the governance_ledger path works after a change.

## 7. ✅ Example Task

**Task:** "Verify enforce-mode ESCALATE end-to-end."
**Expected output:**
- A one-node flow targeting `test-agent` with a `safety: {category: docker}` hint; in `enforce` mode it ESCALATEs → parks `awaiting_approval` → human approves via the dashboard → completes. Confirms HyperFlow ↔ Safety Shepherd ↔ governance all fire.
