import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any
import redis as redis_lib

from app.db.session import get_db
from app.core.config import settings
from app.core.circuit_breaker import all_breakers

router = APIRouter()


class HealthStatus(BaseModel):
    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    version: str
    checks: Dict[str, Any]


def _check_postgres(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_redis() -> dict:
    try:
        r = redis_lib.from_url(
            settings.HYPERCODE_REDIS_URL or "redis://redis:6379/0",
            socket_connect_timeout=2,
        )
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _check_discord() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(
                "https://discord.com/api/v10/gateway",
                headers={"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"},
            )
            return {"status": "ok"} if resp.status_code == 200 else {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/health", response_model=HealthStatus, tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """GET /api/v1/health
    Deep health check — Postgres, Redis, Discord.
    Returns 200 healthy / 207 degraded.
    """
    checks = {
        "postgres": _check_postgres(db),
        "redis": _check_redis(),
        "discord": await _check_discord(),
        "circuit_breakers": all_breakers(),
    }

    infra_checks = {k: v for k, v in checks.items() if k != "circuit_breakers"}
    all_ok = all(v["status"] == "ok" for v in infra_checks.values())
    overall = "healthy" if all_ok else "degraded"

    return HealthStatus(
        status=overall,
        version=settings.VERSION,
        checks=checks,
    )
