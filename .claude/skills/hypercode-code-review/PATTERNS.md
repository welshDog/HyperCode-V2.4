# HyperCode Approved Patterns

## FastAPI agent service template

```python
from fastapi import FastAPI
import redis.asyncio as aioredis
import os

app = FastAPI()

@app.on_event('startup')
async def startup():
    r = aioredis.from_url(f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379")
    await r.publish('hypercode:system', '{"event": "started", "agent": "MY_AGENT"}')
    await r.aclose()

@app.get('/health')
async def health():
    return {"status": "healthy", "agent": "MY_AGENT"}
```

> **Always use `redis.asyncio` (aioredis) — never sync `redis.Redis` in a FastAPI service.**
> FastAPI is async-first; blocking Redis calls stall the event loop.

## Config pattern — ENV ONLY

```python
# GOOD
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY')

# BAD — never hardcode
ANTHROPIC_KEY = 'sk-ant-...'
```

## Structured logging

```python
import structlog
log = structlog.get_logger()
log.info('agent_started', name='my-agent', port=8080)
```
