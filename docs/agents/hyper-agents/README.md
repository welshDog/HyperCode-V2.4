# Hyper-Agents Core Package

> **Location:** `src/agents/hyper_agents/`
> **Branch:** `feature/hyper-agents-core`
> **Architecture:** Additive extension of HyperCode V2.0 — does NOT modify existing agents (Crew, Healer, Brain, Dashboard)

---

## Overview

The `hyper_agents` package introduces a new generation of neurodivergent-friendly (ND-friendly) AI agents for HyperCode V2.0. These agents are designed with clarity, low cognitive overhead, and transparent state management as first-class principles.

### ND-Friendly Design Pillars

| Principle | Implementation |
|---|---|
| **Big picture first** | Every goal is defined with a title + description before any steps execute |
| **Decomposition** | Complex goals broken into `PlanStep` units with explicit dependency graphs |
| **Passive observation** | `ObserverAgent` watches silently — no surprise interruptions |
| **Clear error messages** | `NDErrorResponse` always includes `error_code`, `message`, and `context` |
| **Progress visibility** | `Goal.progress` property provides real-time percentage completion |
| **Graceful degradation** | All agents implement `shutdown()` for clean termination |

---

## Package Structure

```
src/agents/hyper_agents/
├── __init__.py          # Public API surface
├── base_agent.py        # HyperAgent ABC + AgentStatus/AgentArchetype enums
├── architect.py         # ArchitectAgent — planning and goal decomposition
├── observer.py          # ObserverAgent — metric collection and alerting
└── worker.py            # WorkerAgent   — single-task execution specialist
```

---

## Classes

### `HyperAgent` (base_agent.py)
Abstract base class for all hyper-agents. Defines the agent lifecycle:
- `initialize()` → transitions to `IDLE`
- `execute(task)` → abstract method, must be implemented by subclasses
- `shutdown()` → transitions to `TERMINATED`

### `AgentArchetype` (Enum)
```python
AgentArchetype.ARCHITECT  # "architect"
AgentArchetype.WORKER     # "worker"
AgentArchetype.OBSERVER   # "observer"
```

### `AgentStatus` (Enum)
```python
AgentStatus.IDLE
AgentStatus.INITIALIZING
AgentStatus.BUSY
AgentStatus.TERMINATED
```

### `NDErrorResponse`
Structured error object always containing:
- `error_code: str` — machine-readable identifier
- `message: str` — human-readable explanation
- `context: dict` — situational metadata

---

### `ArchitectAgent` (architect.py)

The planning lead. Converts high-level goals into structured step-by-step plans.

**Key methods:**

| Method | Description |
|---|---|
| `create_goal(title, description)` | Creates a new `Goal`, returns `goal_id` |
| `add_step(goal_id, step_id, description, assigned_to, deps)` | Appends a `PlanStep` to a goal |
| `get_ready_steps(goal_id)` | Returns steps whose dependencies are satisfied |
| `update_step_status(goal_id, step_id, status, result, error)` | Updates a step; auto-completes/fails the parent goal |
| `register_agent(agent_id, archetype)` | Tracks available agents for assignment |
| `stats` (property) | Returns a summary dict of current state |

**Example:**
```python
architect = ArchitectAgent(agent_id="lead-01")
await architect.initialize()

goal_id = await architect.create_goal(
    title="Deploy Microservice",
    description="Build, test, and deploy to staging"
)
architect.add_step(goal_id, "build", "Build Docker image")
architect.add_step(goal_id, "test",  "Run test suite", deps={"build"})
architect.add_step(goal_id, "deploy","Deploy to staging", deps={"test"})

# Later, as steps complete:
architect.update_step_status(goal_id, "build", GoalStatus.COMPLETED)
print(architect.get_goal(goal_id).progress)  # 0.333...
```

---

### `ObserverAgent` (observer.py)

Passive system monitor. Collects metrics, detects anomalies, and surfaces insights without interrupting workflows.

**ND-friendly defaults:**
- Silent by default — only alerts when thresholds are explicitly breached
- All observations are logged, nothing is silently discarded

---

### `WorkerAgent` (worker.py)

Single-task execution specialist. Designed for hyperfocus: one task, transparent progress, sensory-safe error reporting.

**Example:**
```python
worker = WorkerAgent(agent_id="worker-01")
await worker.initialize()
result = await worker.execute({"action": "run_linter", "payload": {"path": "./src"}})
```

---

## Testing

Unit tests are located in `tests/unit/test_hyper_agents.py`.

Run with pytest:
```bash
pytest tests/unit/test_hyper_agents.py -v
```

Coverage areas:
- Public API surface (all `__all__` symbols importable)
- `ArchitectAgent`: goal lifecycle, step dependencies, progress calculation
- `ObserverAgent`: initialization, archetype, shutdown
- `WorkerAgent`: initialization, task execution, shutdown
- `NDErrorResponse`: field validation

---

## Integration Notes

- All imports use the package's public API: `from src.agents.hyper_agents import ArchitectAgent`
- The package does NOT modify any existing HyperCode V2.0 components
- Compatible with the existing `AgentArchetype` registry pattern used across the codebase
