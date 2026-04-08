---
name: hypercode-broski-economy
description: Manages the BROski$ coin economy, XP system, achievements, and gamification for HyperCode. Use when awarding coins for completed tasks, leveling up agents or users, checking balances, or triggering achievement unlocks. Publishes all economy events to the BROski$ Redis channel.
---

# BROski$ Economy

## Award coins

```python
import redis, json
r = redis.Redis(host='localhost', port=6379)

def award_broski(user: str, amount: int, reason: str):
    event = {"user": user, "amount": amount, "reason": reason, "type": "award"}
    r.publish('hypercode:broski$', json.dumps(event))
    r.hincrby(f'broski:balance:{user}', 'coins', amount)

# Example
award_broski('lyndz', 50, 'Deployed new agent!')
```

## XP levels

| Level | XP Required | Title |
|-------|-------------|-------|
| 1 | 0 | BROski Initiate |
| 5 | 500 | HyperFocus Apprentice |
| 10 | 2000 | Agent Architect |
| 20 | 10000 | NeuroDivergent Legend |
| MAX | 50000 | BROski♾ Infinite |

## Achievements to auto-trigger

- `first_agent_spawned` → +100 coins
- `system_fully_launched` → +500 coins  
- `skill_improved` → +75 coins
- `guardian_blocked_threat` → +200 coins
- `all_health_green` → +150 coins
