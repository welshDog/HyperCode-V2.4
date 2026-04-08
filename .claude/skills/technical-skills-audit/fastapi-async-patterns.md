# ⚡ FastAPI + Async Python — HyperCode V2.0

## Project Toolchain

| Tool | Config File | Purpose |
|---|---|---|
| Ruff | `ruff.toml` | Fast linter + formatter |
| Pylint | `.pylintrc` | Deep static analysis |
| Pyright | `pyrightconfig.json` | Type checking |
| pytest | `pyproject.toml` (`[tool.pytest.ini_options]`) | Test runner — pytest.ini was removed |
| pyproject.toml | `pyproject.toml` | Project metadata + deps |

## Standard Agent Pattern

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import asyncio

app = FastAPI(title="HyperCode Agent")

class AgentTask(BaseModel):
    task_id: str
    payload: dict
    priority: int = 5

@app.post("/agents/{agent_name}/execute")
async def execute_task(
    agent_name: str,
    task: AgentTask,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(run_agent_task, agent_name, task)
    return {"status": "queued", "task_id": task.task_id}

async def run_agent_task(agent_name: str, task: AgentTask):
    # Agent execution logic here
    await asyncio.sleep(0)  # Yield control
    ...
```

## Redis Pub/Sub Pattern

```python
import redis.asyncio as aioredis

async def publish_agent_event(channel: str, message: dict):
    r = aioredis.from_url("redis://redis:6379")
    await r.publish(channel, json.dumps(message))
    await r.aclose()

async def subscribe_to_events(channel: str):
    r = aioredis.from_url("redis://redis:6379")
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    async for message in pubsub.listen():
        if message["type"] == "message":
            yield json.loads(message["data"])
```

## Testing Conventions

```python
import pytest
import fakeredis.aioredis as fakeredis

@pytest.fixture
async def redis_client():
    client = fakeredis.FakeRedis()
    yield client
    await client.aclose()

@pytest.mark.asyncio
async def test_agent_health(redis_client):
    # Use fakeredis — no live Redis needed in tests
    result = await redis_client.ping()
    assert result is True
```

## Settings Pattern (Pydantic v2)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    postgres_url: str = "postgresql+asyncpg://..."
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```
