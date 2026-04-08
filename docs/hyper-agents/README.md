# Hyper Agents - HyperCode V2.0

**Doc Tag:** v1.0.0 | **Branch:** `feature/hyper-agents-core` | **Status:** In Development

---

## What Hyper Agents Is

Hyper Agents adds a **new layer of modular AI agents** to HyperCode V2.0.

It is **fully additive** - nothing in the existing codebase is changed.
Existing agents (Crew Orchestrator, Healer, The Brain, Dashboard) work exactly as before.

---

## Quick Start (3 steps)

**Step 1 - Install**
```bash
git checkout feature/hyper-agents-core
pip install -r requirements.txt
```

**Step 2 - Create your first agent**
```python
from src.agents.hyper_agents.base_agent import HyperAgent, AgentArchetype

class MyWorker(HyperAgent):
    def __init__(self):
        super().__init__(
            name="my-worker",
            archetype=AgentArchetype.WORKER,
            port=8091,
        )

    async def execute(self, task: dict) -> dict:
        # Your logic here
        return {"status": "done", "message": "Task completed successfully."}

agent = MyWorker()
agent.register_with_crew()  # registers with Crew Orchestrator
agent.set_ready()
```

**Step 3 - Run it**
```bash
uvicorn src.agents.hyper_agents.my_worker.agent:agent.app --port 8091
# Then check: http://localhost:8091/health
```

---

## Architecture

```
HyperCode V2.0 (unchanged)
  Crew Orchestrator (8081)  <-- Hyper Agents register here
  The Brain (cognitive core) <-- Hyper Agents can query this
  Healer Agent (8008/8010)  <-- Monitors all services including Hyper Agents
  Mission Control (8088)    <-- Hyper Agents appear here automatically
  Core API (8000)           <-- Hyper Agents can call shared endpoints

Hyper Agents Layer (NEW - additive)
  src/agents/hyper_agents/
    base_agent.py           <-- Base class all agents extend
    worker/                 <-- Worker archetype
    observer/               <-- Observer archetype
    architect/              <-- Architect archetype
```

**Port allocation:**
- Ports 8091+ are reserved for Hyper Agents.
- Ports 8000, 8008, 8010, 8081, 8088, 3000, 3001 are existing V2.0 services.

---

## Agent Archetypes

| Archetype | Use for | Default port range |
|---|---|---|
| Worker | Background tasks, job processing | 8091-8099 |
| Observer | Monitoring, alerting, telemetry | 8100-8109 |
| Architect | Planning, coordination, scaffolding | 8110-8119 |
| Healer variant | Error recovery, health patching | 8120-8129 |
| Custom | Anything else | 8130+ |

---

## Neurodivergent UX Rules

All Hyper Agents MUST follow these. No exceptions.

**Error messages:** Always structured as:
1. Short title (what failed)
2. What happened (1 sentence)
3. Why it matters (1 sentence)
4. Options (concrete steps, not vague advice)

**Output formatting:**
- Max 3 sentences per block
- Use bullet lists for steps
- No walls of text
- No blame language

**See** `.claude/skills/hypercode-new-agent-onboarding/SKILL.md` for full rules.

---

## Integration Points

### Crew Orchestrator
Call `agent.register_with_crew()` on startup.
The Crew will route tasks to your agent automatically.

### The Brain
Query via `GET http://localhost:8081/brain/query` with your prompt.

### Mission Control Dashboard
Your agent appears automatically when health endpoint responds 200.

### BROski$ (Phase 2)
Agents earn coins for completing tasks. Hook via:
```python
# Coming in Phase 2
await self.award_broski_coins(user_id, 10, "Agent task complete")
```

---

## Development Guide

### Run tests
```bash
pytest tests/hyper_agents/ -v
pytest tests/hyper_agents/ --cov=src/agents/hyper_agents --cov-fail-under=80
```

### Lint
```bash
ruff check src/agents/hyper_agents/
black src/agents/hyper_agents/ tests/hyper_agents/
```

### Add a new agent
See `.claude/skills/hypercode-new-agent-onboarding/SKILL.md` for the full 5-phase workflow.

---

## Integration Timeline (10-week plan)

| Weeks | Milestone |
|---|---|
| 1-2 | Foundation + folder structure in HyperCode V2.0 |
| 3-4 | Core archetypes (Worker, Observer, Architect) |
| 5-6 | SKILL.md + ND UX review |
| 7-8 | 80% coverage + integration tests |
| 9 | Docs + Gate 1 peer review |
| 10 | Gate 2 E2E + Lyndz sign-off + merge to main |

---

## Branch Merge Path

```
feature/hyper-agents-core --> develop --> main
```

**Gate 1** (feature -> develop): 80% coverage, 2 approvals, ND review, CI green.
**Gate 2** (develop -> main): 100% E2E, full stack test, load test, Lyndz sign-off.

---

## Files in This Feature

```
src/agents/hyper_agents/
  base_agent.py             # Base class
tests/hyper_agents/
  unit/                     # Unit tests (80% coverage target)
  integration/              # Integration tests
  e2e/                      # E2E tests (Gate 2)
  nd_ux/                    # ND UX compliance tests
  load/                     # Locust load tests
docs/hyper-agents/
  README.md                 # This file
.claude/skills/
  hypercode-new-agent-onboarding/SKILL.md
.github/workflows/
  hyper-agents-ci.yml       # Gate 1 CI pipeline
  hyper-agents-gate2-e2e.yml # Gate 2 E2E pipeline
.github/ISSUE_TEMPLATE/
  hyper-agent-bug-report.yml
.github/PULL_REQUEST_TEMPLATE/
  hyper-agents-pr.md
```

---

## Need Help?

- **Stuck / confused?** Open an issue using the Bug Report template.
- **Want to add an agent?** Use the SKILL.md onboarding workflow.
- **Questions about ND UX rules?** See the main `CONTRIBUTING.md` and the ND design section.
- **Docs for existing V2.0 features?** See `docs/index.md`.

**Remember: No blame. No judgment. We build this together.** BROski style.
