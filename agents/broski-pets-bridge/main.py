import os

import httpx
import redis
from fastapi import FastAPI


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


app = FastAPI(title="broski-pets-bridge")


@app.get("/health")
async def health() -> dict:
    ollama_url = os.getenv("OLLAMA_URL", "http://hypercode-ollama:11434").rstrip("/")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/3")
    pets_enabled = _is_true(os.getenv("PETS_ENABLED"))

    ollama_connected = False
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            ollama_connected = resp.status_code == 200
    except Exception:
        ollama_connected = False

    redis_connected = False
    try:
        r = redis.from_url(redis_url, socket_timeout=2, decode_responses=True)
        redis_connected = r.ping() is True
    except Exception:
        redis_connected = False

    return {
        "status": "ok",
        "service": "broski-pets-bridge",
        "pets_enabled": pets_enabled,
        "ollama_connected": ollama_connected,
        "redis_connected": redis_connected,
        "redis_db": 3,
    }
