# 💡 Tips & Tricks #4: FastAPI Optimization

Bro, your API shouldn't just work—it should **scream**. 🏎️ When your HyperCode agents are hitting endpoints, every millisecond counts. Let's optimize your **FastAPI** stack.

---

## 🟢 1. Uvicorn Workers (Low Complexity)

By default, Uvicorn runs on a single process. On a multi-core machine, that's like having a V8 engine but only using one cylinder.

**The Fix**: Use multiple workers to handle more concurrent requests.

**Copy-Paste for `Dockerfile` or Start Script**:
```bash
# Rule of thumb: (2 x cores) + 1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

- **Why?**: If one request is heavy (e.g., processing a large PDF), other workers can still handle incoming traffic.
- **Pro Tip**: Don't go overboard. Too many workers = context switching overhead. Stick to the formula.

---

## 🟡 2. Async Pitfalls (Medium Complexity)

The biggest killer of FastAPI performance is **blocking the event loop**. If you use a synchronous library inside an `async def` function, you stop the entire API for everyone.

**Copy-Paste: The Right Way vs. The Wrong Way**:
```python
# ❌ BAD: Blocks the whole API
@app.get("/bad")
async def bad_route():
    import time
    time.sleep(5) # The entire server stops here for 5 seconds!
    return {"status": "slow"}

# ✅ GOOD: Non-blocking
@app.get("/good")
async def good_route():
    import asyncio
    await asyncio.sleep(5) # Only this request waits; others keep flying
    return {"status": "fast"}
```

- **Rule**: If a library doesn't support `await`, run it in a threadpool using `run_in_executor` or just define the route as `def` (without `async`), and FastAPI will handle the threading for you.

---

## 🔴 3. Redis Caching (High Complexity)

Why compute the same thing twice? If an agent asks for the same system audit report 10 times, fetch it from **Redis** after the first time.

**Copy-Paste: FastCaché Pattern**:
```python
import redis
from fastapi import Depends

# Connect to our HyperCode Redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.get("/audit/{project_id}")
async def get_audit(project_id: str):
    # 1. Check Cache
    cached_data = r.get(f"audit:{project_id}")
    if cached_data:
        return {"data": cached_data, "source": "cache"}

    # 2. Heavy Computation (Mock)
    data = await perform_heavy_audit(project_id)

    # 3. Store in Cache (Expires in 1 hour)
    r.setex(f"audit:{project_id}", 3600, data)
    
    return {"data": data, "source": "db"}
```

- **Risk**: Cache invalidation is hard. If the project changes, you **must** delete the old cache key.
- **Benefit**: Can reduce response times from **2 seconds** to **2 milliseconds**.

---

## 🎯 4. Success Criteria

You've officially optimized your stack when:
1. `htop` shows multiple Uvicorn processes sharing the load.
2. Your logs show `source: cache` for repeat requests.
3. Your **Grafana** dashboard shows a flat line for latency, even under load.

**Next Action, Bro**: 
Check your most expensive endpoint. If it's doing heavy math or DB lookups, drop that **Redis Caching** pattern in and watch the speed boost! 🚀
