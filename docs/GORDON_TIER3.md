# Gordon Tier 3 — Implementation Notes

> Completed: April 16, 2026
> Status: DONE ✅

---

## What Changed

### Part A — Native Async DB Engine (`backend/app/db/session.py`)

**Added:**

- `asyncpg==0.30.0` to `backend/requirements.txt`
- `async_engine` — a real `create_async_engine` using the `postgresql+asyncpg://` driver
- `_AsyncSessionFactory` — `async_sessionmaker` bound to `async_engine`
- `get_async_db()` — FastAPI `Depends()`-compatible async generator that yields a native `AsyncSession`

**Kept (unchanged):**

- Sync `engine` + `SessionLocal` + `get_db()` — Celery workers and Alembic still use these
- `_AsyncSessionProxy` + `AsyncSessionLocal()` context manager — Phase 10G/10D callers still work

**Pool config:**

```
pool_size=10          — up to 10 concurrent connections kept alive
max_overflow=20       — burst up to 30 total if pool is full
pool_pre_ping=True    — see explanation below
pool_recycle=3600     — retire connections older than 1 hour
```

**How to use `get_async_db` in a new route:**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import Depends
from app.db.session import get_async_db

@router.get("/example")
async def example(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(text("SELECT 1"))
    return {"ok": True}
```

---

### Part B — Celery Reliability (`backend/app/core/celery_app.py` + `backend/app/worker.py`)

**`celery_app.py` additions:**

```python
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
```

**`worker.py` additions:**

- `run_agent_task` Celery task with `bind=True`, `max_retries=3`, `default_retry_delay=30`
- Exponential-backoff retry: `countdown=2 ** self.request.retries` → 1s, 2s, 4s
- Registered as `hypercode.tasks.run_agent_task` on `main-queue`

**Enqueue from anywhere:**

```python
from app.worker import run_agent_task

run_agent_task.delay(
    agent_name="healer-agent",
    task_type="diagnose",
    payload={"container": "hypercode-core"},
    task_id="abc-123",
)
```

---

## Why `pool_pre_ping=True` Matters

Before returning a pooled connection to your code, SQLAlchemy fires a lightweight `SELECT 1` ("ping").

- If the connection is **alive** → returned immediately (adds ~0.1ms)
- If the connection is **dead** (postgres restarted, TCP timeout, Docker network blip) → discarded, a fresh connection is opened

**Without it:** your first request after any downtime crashes with `OperationalError: server closed the connection unexpectedly`.

**With it:** transparent recovery — users never see DB errors from stale connections.

This is especially important in Docker environments where containers restart independently and TCP sessions can silently drop.

---

## Verification

### Async engine import check

```bash
cd /path/to/HyperCode-V2.4
python -c "
import sys; sys.path.insert(0, 'backend')
from app.db.session import async_engine, get_async_db, AsyncSessionLocal
print('async_engine:', async_engine)
print('✅ All async DB imports OK')
"
```

### Live DB round-trip (needs running stack)

```bash
curl -s http://localhost:8000/health | python -m json.tool
# Should return {"status": "ok", ...}
```

### Celery task dispatch test

```bash
docker exec hypercode-celery-worker python -c "
from app.worker import run_agent_task
result = run_agent_task.apply(args=[], kwargs={
    'agent_name': 'test',
    'task_type': 'general',
    'payload': {'description': 'ping'},
})
print('Result:', result.get(timeout=30))
"
```

### Verify Celery config

```bash
docker exec hypercode-celery-worker python -c "
from app.core.celery_app import celery_app
print('task_acks_late:', celery_app.conf.task_acks_late)
print('prefetch_multiplier:', celery_app.conf.worker_prefetch_multiplier)
"
# Expected: task_acks_late: True, prefetch_multiplier: 1
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/requirements.txt` | Added `asyncpg==0.30.0` |
| `backend/app/db/session.py` | Added `async_engine`, `_AsyncSessionFactory`, `get_async_db()` |
| `backend/app/core/celery_app.py` | Added `task_acks_late=True`, `worker_prefetch_multiplier=1`, JSON serializer config |
| `backend/app/worker.py` | Added `run_agent_task` with `max_retries=3` + exponential-backoff retry |
| `docs/GORDON_TIER3.md` | This file |
