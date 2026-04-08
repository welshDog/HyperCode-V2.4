# 💡 Tips & Tricks #6: Agent State Management

Bro, an agent that forgets is just a script. 🧠 To build a legendary AI ecosystem, your agents need to manage their state like pros. Let's dive into **State Management** for HyperCode agents.

---

## 🟢 1. In-Memory vs. Persistent State (Low Complexity)

Where should your agent keep its thoughts? You have two main choices: **Memory** (RAM) or **Persistence** (Redis/DB).

- **Memory (RAM)**: Fast but disappears if the container restarts. Use this for temporary "scratchpad" thoughts during a single task.
- **Persistence (Redis)**: Still fast, but survives restarts. Use this for "Long-Term Memory" like user preferences, mission progress, or agent "moods."

**The Golden Rule**: If it matters tomorrow, put it in Redis. If it only matters for the next 5 seconds, keep it in a local variable.

---

## 🟡 2. The FastAPI State Pattern (Medium Complexity)

Our HyperCode agents use **FastAPI** to communicate. You can use the `app.state` object to share data across different parts of your agent.

**Copy-Paste: `agent.py` State Logic**:
```python
from fastapi import FastAPI, Request
import redis

app = FastAPI()
r = redis.Redis(host='redis', port=6379, decode_responses=True)

# 1. Initialize global state on startup
@app.on_event("startup")
async def startup_event():
    app.state.mission_count = 0
    app.state.redis = r

# 2. Update state in a route
@app.post("/execute")
async def execute_task(request: Request):
    app.state.mission_count += 1
    # Save to Redis for persistence
    app.state.redis.set("total_missions", app.state.mission_count)
    return {"status": "crushing_it", "missions": app.state.mission_count}
```

- **Why?**: It keeps your code clean and makes it easy to access shared resources (like a Redis connection) anywhere in your agent.

---

## 🔴 3. Race Conditions & State Drift (High Complexity)

When multiple agents or multiple workers are updating the same state at once, things get messy. This is called a **Race Condition**. 🏎️💨

**The Risk**:
- Agent A reads state (value = 10).
- Agent B reads state (value = 10).
- Agent A updates to 11.
- Agent B updates to 11 (should have been 12!).
- **Result**: You just lost a mission update. Bro, not cool.

**The Fix: Atomic Operations**:
```python
# ❌ BAD: Read-Modify-Write (Not Atomic)
val = r.get("counter")
r.set("counter", int(val) + 1)

# ✅ GOOD: Atomic Increment
r.incr("counter") # Redis handles the math safely in one step!
```

---

## 🎯 4. Success Criteria

You've mastered the state if:
1. Your agent remembers its mission even after a `docker compose restart`.
2. You aren't seeing "State Drift" where counters don't match reality.
3. Your `agent.py` uses `app.state` to avoid messy global variables.

**Next Action, Bro**: 
Check your agent's `process_task` logic. If it's using global variables for anything important, move them to `app.state` and back them up to Redis! 🚀
