# Consciousness Protocol Reference

## Pulse cadence
- Normal operation: every 30 seconds
- Under stress (saturation > 0.7): every 10 seconds
- Critical state (saturation > 0.9): every 5 seconds + immediate alert

## Thresholds quick-reference

| Metric | Warning | Critical | Action |
|---|---|---|---|
| context_saturation | > 0.75 | > 0.85 | HyperSync handoff |
| confidence | < 0.6 | < 0.4 | Flag for review |
| confusion_score | > 0.5 | > 0.7 | Request specialist |
| task_queue_depth | > 7 | > 15 | Request clone spawn |

## Petition priority levels
- `low` — nice-to-have, schedule for next sprint
- `normal` — needed within 48h
- `high` — impacting live tasks now
- `critical` — blocking all work, immediate action required

## Agent X response SLA
- `low` petitions: evaluated in next evolution cycle (hourly)
- `normal` petitions: evaluated within 15 minutes
- `high` / `critical` petitions: evaluated immediately on receipt

## Consciousness health score formula
```
health_score = (confidence * 0.4) + ((1 - confusion_score) * 0.3) + ((1 - context_saturation) * 0.3)
```
Score > 0.8 = healthy
Score 0.5–0.8 = watch
Score < 0.5 = intervene
