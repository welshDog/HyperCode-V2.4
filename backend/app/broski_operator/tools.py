"""Local (in-core) tools that HyperFlow ``tool`` nodes can run without the orchestrator.

``inspect_stack`` is strictly read-only: Docker via the read-only socket proxy (GET only),
Redis PING, Postgres ``SELECT 1``, Celery queue depths (LLEN), disk usage, model list.
Each section is independent, time-limited and fail-soft.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx
import redis.asyncio as aioredis
from sqlalchemy import text

from app.broski_operator.recover import scrub_text
from app.core.config import settings
from app.db.session import SessionLocal

SECTION_TIMEOUT_SECONDS = 8.0
_QUEUES = ("hypercode-high", "hypercode-normal", "hypercode-low", "hypercode-dlq")
_MAX_NAMES = 50
_CORE_SECTIONS = ("containers", "redis", "postgres")


async def _docker_section() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/json", params={"all": "true"}
        )
    resp.raise_for_status()
    rows = resp.json()

    def names(items: list[dict[str, Any]]) -> list[str]:
        return sorted((c.get("Names") or ["?"])[0].lstrip("/") for c in items)[:_MAX_NAMES]

    return {
        "ok": True,
        "total": len(rows),
        "running": sum(1 for c in rows if c.get("State") == "running"),
        "exited": names([c for c in rows if c.get("State") == "exited"]),
        "unhealthy": names([c for c in rows if "unhealthy" in (c.get("Status") or "")]),
    }


async def _redis_section() -> dict[str, Any]:
    r = aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        await r.ping()
    finally:
        await r.aclose()
    return {"ok": True}


def _pg_ping() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()


async def _postgres_section() -> dict[str, Any]:
    try:
        await asyncio.to_thread(_pg_ping)
    except Exception as exc:
        # Driver messages carry host/user/SQL: expose only the exception type.
        raise RuntimeError(f"postgres check failed ({type(exc).__name__})") from None
    return {"ok": True}


async def _queues_section() -> dict[str, Any]:
    from app.core.celery_app import celery_app

    r = aioredis.from_url(celery_app.conf.broker_url, decode_responses=True)
    try:
        depths = {q: int(await r.llen(q)) for q in _QUEUES}
    finally:
        await r.aclose()
    return {"ok": True, "depths": depths}


async def _disk_section() -> dict[str, Any]:
    du = shutil.disk_usage("/")
    used_pct = round(100 * du.used / du.total, 1)
    return {"ok": used_pct < 90.0, "free_gb": round(du.free / 1e9, 1), "used_pct": used_pct}


async def _models_section() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.OLLAMA_HOST.rstrip('/')}/api/tags")
    resp.raise_for_status()
    return {"ok": True, "models": [m.get("name") for m in resp.json().get("models", [])][:10]}


def _safe_error(exc: BaseException) -> str:
    """Render an exception for persisted/API output without leaking URLs or credentials."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return f"timed out after {SECTION_TIMEOUT_SECONDS:g}s"
    msg = scrub_text(str(exc))
    return f"{type(exc).__name__}: {msg[:120]}" if msg else type(exc).__name__


async def _section(fn: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(fn(), timeout=SECTION_TIMEOUT_SECONDS)
    except Exception as exc:  # fail-soft by design: a broken dependency is a finding, not a crash
        return {"ok": False, "error": _safe_error(exc)}


async def inspect_stack(params: dict[str, Any], ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read-only stack health report. Never raises."""
    fns = {
        "containers": _docker_section,
        "redis": _redis_section,
        "postgres": _postgres_section,
        "queues": _queues_section,
        "disk": _disk_section,
        "models": _models_section,
    }
    results = await asyncio.gather(*(_section(fn) for fn in fns.values()))
    report: dict[str, Any] = dict(zip(fns.keys(), results))

    attention: list[str] = []
    for name, section in report.items():
        if not section.get("ok"):
            attention.append(f"{name}: {section.get('error') or 'not ok'}")
    unhealthy = report["containers"].get("unhealthy") or []
    if unhealthy:
        attention.append(f"unhealthy containers: {', '.join(unhealthy)}")
    dlq = (report["queues"].get("depths") or {}).get("hypercode-dlq", 0)
    if dlq:
        attention.append(f"dead-letter queue has {dlq} tasks")

    return {
        "ok": all(report[k].get("ok") for k in _CORE_SECTIONS),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "attention": attention,
        **report,
    }


LOCAL_TOOLS: dict[str, Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "local.inspect": inspect_stack,
}

from app.broski_operator.recover_tools import recover_propose, recover_seal  # noqa: E402

LOCAL_TOOLS["local.recover_propose"] = recover_propose
LOCAL_TOOLS["local.recover_seal"] = recover_seal

from app.broski_operator.authorize_tools import authorize  # noqa: E402

LOCAL_TOOLS["local.authorize"] = authorize

from app.crew.tools import crew_guard, crew_plan, crew_seal, crew_settle  # noqa: E402

LOCAL_TOOLS["local.crew_plan"] = crew_plan
LOCAL_TOOLS["local.crew_seal"] = crew_seal
LOCAL_TOOLS["local.crew_guard"] = crew_guard
LOCAL_TOOLS["local.crew_settle"] = crew_settle
