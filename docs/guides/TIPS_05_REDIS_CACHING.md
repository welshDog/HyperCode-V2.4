# 💡 Tips & Tricks #5: Redis Caching & Pub/Sub

Bro, if your agents are talking to each other, they need a fast lane. ⚡ **Redis** isn't just a database; it's the nervous system of the HyperCode ecosystem. Let's wire it up.

---

## 🟢 1. Caching Agent State (Low Complexity)

Agents often need to remember small bits of info between requests. Storing this in a heavy DB like Postgres is overkill. Use Redis for **Instant Recall**.

**Copy-Paste: Agent State Pattern**:
```python
import redis
import json

# Connect to the HyperCode Redis bus
r = redis.Redis(host='redis', port=6379, decode_responses=True)

def save_agent_mood(agent_id, mood):
    # Store state with a 10-minute TTL (Time To Live)
    r.setex(f"agent:{agent_id}:mood", 600, json.dumps({"mood": mood}))

def get_agent_mood(agent_id):
    state = r.get(f"agent:{agent_id}:mood")
    return json.loads(state) if state else {"mood": "neutral"}
```

- **Why?**: It's memory-speed. No disk I/O.
- **Pro Tip**: Use `setex` so you don't leak memory with old state.

---

## 🟡 2. Connection Pooling (Medium Complexity)

Opening and closing a connection for every request is slow. It's like calling your bro, saying one word, and hanging up 100 times a minute. 📵

**Copy-Paste: The Pool Pattern**:
```python
import redis

# Create a pool once when your agent starts
pool = redis.ConnectionPool(host='redis', port=6379, db=0, max_connections=20)

def get_redis_client():
    return redis.Redis(connection_pool=pool)

# Use it in your FastAPI dependency
from fastapi import Depends

@app.get("/data")
async def get_data(r: redis.Redis = Depends(get_redis_client)):
    return {"val": r.get("key")}
```

- **Why?**: Reuses existing connections. Saves CPU and reduces latency.
- **Rule**: Never create a new `Redis()` instance inside a loop or a hot route!

---

## 🔴 3. Pub/Sub for Agent Comms (High Complexity)

Want Agent A to trigger Agent B instantly? Use **Pub/Sub (Publish/Subscribe)**. It's like a radio station for your agents.

**Copy-Paste: The Radio Pattern**:
```python
# --- AGENT A (The Sender) ---
r.publish("agent-mission-control", "Mission Started: Phase 1")

# --- AGENT B (The Listener) ---
pubsub = r.pubsub()
pubsub.subscribe("agent-mission-control")

for message in pubsub.listen():
    if message['type'] == 'message':
        print(f"BRO, new orders: {message['data']}")
```

- **Risk**: Pub/Sub is "fire and forget." If Agent B is offline when Agent A sends the message, it's gone forever.
- **Solution**: For critical tasks, use **Redis Streams** or a Task Queue (like Celery) instead.

---

## 🎯 4. Success Criteria

You've mastered the Redis lane when:
1. Agent state persists across restarts (if no TTL) but loads instantly.
2. Your connection logs don't show "Too many open files" (thanks to pooling).
3. Agents react to events in **real-time** via the Pub/Sub bus.

**Next Action, Bro**: 
Identify one piece of state your agent fetches frequently. Cache it in Redis with a 5-minute TTL and feel the speed! 🚀
