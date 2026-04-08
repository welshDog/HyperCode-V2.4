# Eval Examples

## Agent Spawner Evals

```json
[
  {
    "skill": "hypercode-agent-spawner",
    "query": "Spawn a new data-analysis agent",
    "expected_behavior": ["Creates agent spec", "Registers in crew", "Adds to docker-compose"]
  },
  {
    "skill": "hypercode-agent-spawner",
    "query": "Add a guardian enforcement agent",
    "expected_behavior": ["Sets safety_level to strict", "Wires to guardian channel"]
  }
]
```

## Self-Improver Evals

```json
[
  {
    "skill": "hypercode-self-improver",
    "query": "Run evals on all skills",
    "expected_behavior": ["Runs eval mode", "Produces score report", "Identifies failing skills"]
  }
]
```
