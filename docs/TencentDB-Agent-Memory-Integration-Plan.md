# TencentDB Agent Memory Integration Plan for HyperCode V2.4

> Written: 11 August 2026 | Status: Pilot Planning | Owner: welshDog

## Why

HyperCode V2.4 currently manages memory and context inside the FastAPI HyperCode Core, mixed in with orchestration logic for the 32-agent swarm. TencentDB Agent Memory (github.com/TencentCloud/TencentDB-Agent-Memory) offers a dedicated, governed memory layer with four reusable asset types: Chat Memory, Skill, LLM-Wiki, and Code-Graph. It fits naturally alongside our existing MCP gateway (hyper-mcp-server) since it is designed to be plugged into agent frameworks via MCP-style access.

## Fit Map

| HyperCode Need | TencentDB Asset |
|---|---|
| Agent X (Meta-Architect) reusing proven agent designs | Skill |
| Crew Orchestrator cross-mission continuity | Chat Memory |
| Healer Agent recalling past incidents/fixes | Skill + Chat Memory |
| Impact analysis across 48-container stack | Code-Graph |
| Querying MASTER-INDEX / START_HERE / STATUS_REPORT | LLM-Wiki |
| Isolating what each of the 32 agents can see | Team/agent permissions + loadouts |

## Phased Plan

### Phase 1 - Isolated Pilot
- Deploy TencentDB Agent Memory v2.0.0 via Docker Compose as a standalone service, separate from the 48-container HyperCode stack.
- Point hyper-mcp-server at it as an additional MCP tool endpoint (read-only to start).
- Create 3 test agents mirroring real ones: agent-x, healer, devops.
- Load STATUS_REPORT.md, MASTER-INDEX.md, START_HERE.md into LLM-Wiki.
- Run Code-Graph indexing on one subsystem only (not the full repo yet).

### Phase 2 - Wire into MCP Gateway
- Expose memory.recall, memory.skill.get, and codegraph.impact as native MCP tools inside HyperCode Core.
- Agent X logs every new agent design as a Skill entry to avoid reinventing agent designs.
- Healer Agent writes incident+fix pairs to Skill memory for faster future recovery.

### Phase 3 - Governance Layer
- Formally separate read/write memory access per agent using TencentDB's team/agent permission model and loadouts.
- Extend Code-Graph across the full repo so PRs (currently 138 open) get automated impact analysis before merge.

### Phase 4 - Validation Metrics
- Time for Agent X to design a new agent (expect reduction via Skill reuse).
- Healer Agent mean-time-to-recovery.
- Reduction in duplicate/conflicting PRs across 156 branches.
- Token spend per agent task (expect reduction via targeted loadouts vs full context dumps).

## Cautions Before Wider Rollout
- TencentDB-Agent-Memory license shows as Other/NOASSERTION on GitHub, not a standard MIT/Apache tag - review LICENSE file directly before deeper integration.
- Default branch is feat/server_team (not main) with 630+ open issues - pin a specific tagged release (v2.0.0) rather than tracking the moving branch.
- Keep as an isolated sidecar service until Phase 1 proves stable; do not merge into the 48-container critical path prematurely.
- Verify tenant isolation, data export/deletion, and compatibility with our existing Supabase/Postgres setup.

## Next Action
Start Phase 1 pilot scoped to the Healer Agent only, since recall-of-past-fixes has the clearest and fastest payoff.
