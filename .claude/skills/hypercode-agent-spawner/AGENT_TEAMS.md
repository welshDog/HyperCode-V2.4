# Agent Teams Pattern

Agent Teams allow one orchestrator to spawn parallel specialist agents that share context and coordinate output.

## When to use

- Task has 3+ distinct specialist domains
- Subtasks can run in parallel
- Output needs cross-validation between agents

## Team spawn pattern

```python
team = [
    {"role": "researcher", "tools": ["web_search", "memory_read"]},
    {"role": "implementer", "tools": ["code_write", "docker_exec"]},
    {"role": "reviewer", "tools": ["code_read", "test_run"]},
]
# Crew Orchestrator coordinates via Redis streams
```

## Coordination channel

All team agents publish to: `hypercode:teams:<team_id>:events`
Orchestrator subscribes and merges results.
