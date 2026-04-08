---
name: hypercode-self-improver
description: Runs the HyperCode Skills 2.0 self-improvement loop. Tests, scores, and rewrites agent skills and prompts automatically using binary eval criteria. Use when asked to improve a skill, run evals, benchmark performance, or trigger the Karpathy autoresearch loop. This is the evolutionary pipeline trigger.
---

# HyperCode Self-Improver

## 4 modes

1. **Eval** — pass/fail test suite against a skill
2. **Benchmark** — track score across model versions
3. **Improve** — rewrite skill description + instructions to fix failures
4. **Trigger Optimizer** — fix false-positive/negative skill activations

## Run eval

```bash
python scripts/skill_eval.py --skill <skill-name> --mode eval
```

## Run improve loop

```bash
python scripts/skill_eval.py --skill <skill-name> --mode improve --iterations 5
```

Loop:
1. Run evals → get pass/fail results
2. Analyze failures → identify pattern
3. Rewrite `SKILL.md` description + instructions
4. Re-run evals → confirm improvement
5. Commit if score improved

## Eval format

```json
{
  "skill": "hypercode-agent-spawner",
  "query": "Create a new memory agent on port 8090",
  "expected_behavior": [
    "Generates valid agent_spec.json",
    "Registers agent in Crew Orchestrator",
    "Adds health check endpoint"
  ]
}
```

See [EVAL_EXAMPLES.md](EVAL_EXAMPLES.md) for full test suite.
