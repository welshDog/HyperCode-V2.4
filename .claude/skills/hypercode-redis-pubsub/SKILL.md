---
name: hypercode-redis-pubsub
description: Manages Redis pub/sub channels, streams, and memory for HyperCode inter-agent communication. Use when inspecting agent messages, publishing system events, debugging communication between agents, or wiring new agents into the event bus. Knows all HyperCode channel naming conventions.
---

# HyperCode Redis Pub/Sub

## Channel naming convention

```
hypercode:system          → system-wide broadcast
hypercode:agents:<name>   → agent-specific messages
hypercode:teams:<id>      → agent team coordination
hypercode:guardian:blocks → blocked actions log
hypercode:health          → health pulse events
hypercode:broski$         → BROski coin economy events
```

## Quick operations

```python
import redis
r = redis.Redis(host='localhost', port=6379)

# Publish event
r.publish('hypercode:system', '{"event": "agent_started", "name": "agent-x"}')

# Subscribe to channel
pubsub = r.pubsub()
pubsub.subscribe('hypercode:health')
for msg in pubsub.listen():
    print(msg)

# Stream append (persistent log)
r.xadd('hypercode:events', {'type': 'startup', 'service': 'core'})

# Read last 10 events
r.xrevrange('hypercode:events', count=10)
```

## Debug inter-agent comms

```bash
# Monitor ALL channels live
redis-cli MONITOR

# Subscribe to system channel
redis-cli SUBSCRIBE hypercode:system

# Check stream length
redis-cli XLEN hypercode:events
```
