import httpx
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any
import redis as redis_lib

from app.db.session import get_db, probe_db
from app.core.config import settings
from app.core.circuit_breaker import all_breakers

router = APIRouter()


class HealthStatus(BaseModel):
    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    version: str
    checks: Dict[str, Any]


def _check_postgres(db: Session) -> dict:
    """Check Postgres by running a lightweight query on the injected session.

    Also updates the module-level ``_db_available`` flag in db.session so
    that the root ``/health`` endpoint reflects the current state.
    """
    try:
        db.execute(text("SELECT 1"))
        # Sync the availability flag so /health picks up recovery.
        probe_db()
        return {"status": "ok"}
    except Exception as e:
        probe_db()
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
        return {"status": "error", "detail": str(e), "fallback": "in-memory"}


async def _check_discord() -> dict:
    if not settings.DISCORD_BOT_TOKEN:
        return {"status": "skipped", "detail": "DISCORD_BOT_TOKEN not configured"}
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
async def health_check(response: Response, db: Session = Depends(get_db)):
    """GET /api/v1/health

    Deep health check — Postgres, Redis, Discord, circuit breakers.

    HTTP status codes:
      200 — all core services healthy
      503 — Postgres unavailable (app running in degraded mode)
    """
    checks = {
        "postgres": _check_postgres(db),
        "redis": _check_redis(),
        "discord": await _check_discord(),
        "circuit_breakers": all_breakers(),
    }

    # Postgres is a *core* dependency — its failure drives the HTTP status.
    postgres_ok = checks["postgres"]["status"] == "ok"
    # Redis and Discord are non-critical; their failure only affects `status`.
    non_core_ok = all(
        v["status"] in {"ok", "skipped"}
        for k, v in checks.items()
        if k not in {"postgres", "circuit_breakers"}
    )

    if not postgres_ok:
        overall = "unhealthy"
        response.status_code = 503
    elif not non_core_ok:
        overall = "degraded"
        # Still 200 — app is functional, non-critical services are down.
    else:
        overall = "healthy"

    return HealthStatus(
        status=overall,
        version=settings.VERSION,
        checks=checks,
    )
