"""
HyperHealth Async Worker
Runs continuously — executes checks, stores results, triggers self-healing.
Run: python -m worker
"""
from __future__ import annotations

import asyncio
import os
import ssl
import socket
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from models import CheckDefinitionORM, CheckResultORM

# ── Structured logging — FIXED: no add_logger_name ────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

# ── Config ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set")

ASYNC_DB_URL = (
    DATABASE_URL
    if "asyncpg" in DATABASE_URL
    else DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
HEALER_URL = os.environ.get("HEALER_URL", "http://healer-agent:8008")
WORKER_CONCURRENCY = int(os.environ.get("WORKER_CONCURRENCY", "50"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LIVENESS_KEY = "hyperhealth:worker:heartbeat"

# ── DB Engine ─────────────────────────────────────────────────────────────────
engine = create_async_engine(
    ASYNC_DB_URL, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ── Shared HTTP client ───────────────────────────────────────────────────────────
HTTP_CLIENT: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    global HTTP_CLIENT
    if HTTP_CLIENT is None or HTTP_CLIENT.is_closed:
        HTTP_CLIENT = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(10.0),
        )
    return HTTP_CLIENT


# ── Check Executors ───────────────────────────────────────────────────────────
async def execute_http_check(target: str, thresholds: Dict) -> Dict[str, Any]:
    client = await get_http_client()
    start = time.monotonic()
    try:
        resp = await client.get(target)
        latency_ms = (time.monotonic() - start) * 1000
        warn_lat = thresholds.get("latency_ms", {}).get("warn", 1000)
        crit_lat = thresholds.get("latency_ms", {}).get("crit", 3000)
        if resp.status_code >= 400:
            status = "CRIT"
        elif latency_ms >= crit_lat:
            status = "CRIT"
        elif latency_ms >= warn_lat:
            status = "WARN"
        else:
            status = "OK"
        return {"status": status, "latency_ms": latency_ms,
                "value": float(resp.status_code), "message": f"HTTP {resp.status_code} in {latency_ms:.0f}ms"}
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "CRIT", "latency_ms": latency_ms, "value": None, "message": str(exc)}


async def execute_tls_check(target: str, thresholds: Dict) -> Dict[str, Any]:
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        host, _, port_str = host.partition(":")
        port = int(port_str) if port_str else 443
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
        conn.settimeout(10)
        conn.connect((host, port))
        cert = conn.getpeercert()
        conn.close()
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days_left = (not_after - datetime.utcnow()).days
        warn_days = thresholds.get("days_to_expiry", {}).get("warn", 30)
        crit_days = thresholds.get("days_to_expiry", {}).get("crit", 7)
        status = "CRIT" if days_left <= crit_days else "WARN" if days_left <= warn_days else "OK"
        return {"status": status, "latency_ms": None, "value": float(days_left),
                "message": f"TLS cert expires in {days_left} days"}
    except Exception as exc:
        return {"status": "CRIT", "latency_ms": None, "value": None, "message": str(exc)}


async def execute_db_check(target: str, thresholds: Dict) -> Dict[str, Any]:
    import asyncpg
    start = time.monotonic()
    try:
        conn = await asyncpg.connect(target, timeout=10)
        await conn.fetchval("SELECT 1")
        await conn.close()
        latency_ms = (time.monotonic() - start) * 1000
        warn_lat = thresholds.get("latency_ms", {}).get("warn", 200)
        crit_lat = thresholds.get("latency_ms", {}).get("crit", 1000)
        status = "CRIT" if latency_ms >= crit_lat else "WARN" if latency_ms >= warn_lat else "OK"
        return {"status": status, "latency_ms": latency_ms, "value": 1.0,
                "message": f"DB responded in {latency_ms:.0f}ms"}
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "CRIT", "latency_ms": latency_ms, "value": None, "message": str(exc)}


async def execute_cache_check(target: str, thresholds: Dict) -> Dict[str, Any]:
    import redis.asyncio as aioredis
    start = time.monotonic()
    try:
        r = aioredis.from_url(target, socket_timeout=5)
        await r.ping()
        await r.set("hyperhealth:probe", "1", ex=10)
        val = await r.get("hyperhealth:probe")
        await r.aclose()
        latency_ms = (time.monotonic() - start) * 1000
        ok = val == b"1"
        return {"status": "OK" if ok else "CRIT", "latency_ms": latency_ms,
                "value": 1.0 if ok else 0.0, "message": f"Redis ping+set/get in {latency_ms:.0f}ms"}
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "CRIT", "latency_ms": latency_ms, "value": None, "message": str(exc)}


async def execute_check(check: CheckDefinitionORM) -> Dict[str, Any]:
    dispatchers = {
        "http": execute_http_check,
        "tls": execute_tls_check,
        "db": execute_db_check,
        "cache": execute_cache_check,
    }
    executor = dispatchers.get(check.type)
    if executor:
        return await executor(check.target, check.thresholds or {})
    return {"status": "UNKNOWN", "latency_ms": None, "value": None,
            "message": f"Check type '{check.type}' not yet implemented"}


# ── Storage & self-heal ───────────────────────────────────────────────────────────
async def store_result(check: CheckDefinitionORM, result: Dict, started_at: datetime):
    async with SessionLocal() as db:
        row = CheckResultORM(
            id=uuid.uuid4(),
            check_id=check.id,
            status=result["status"],
            latency_ms=result.get("latency_ms"),
            value=result.get("value"),
            message=result.get("message"),
            environment=check.environment,
            started_at=started_at,
            finished_at=datetime.utcnow(),
        )
        db.add(row)
        await db.commit()


async def maybe_trigger_selfheal(check: CheckDefinitionORM, result: Dict):
    if result["status"] != "CRIT" or not check.self_heal_policy_id:
        return
    try:
        client = await get_http_client()
        payload = {"agent_name": check.name, "action": "restart",
                   "environment": check.environment, "source": "hyperhealth-worker"}
        resp = await client.post(f"{HEALER_URL}/heal", json=payload)
        log.info("selfheal.dispatched", check=check.name, status=resp.status_code)
    except Exception as exc:
        log.error("selfheal.error", check=check.name, error=str(exc))


async def write_heartbeat():
    import redis.asyncio as aioredis
    try:
        r = aioredis.from_url(REDIS_URL, socket_timeout=5)
        await r.set(LIVENESS_KEY, datetime.utcnow().isoformat(), ex=90)
        await r.aclose()
    except Exception as exc:
        log.warning("heartbeat.failed", error=str(exc))


# ── Scheduler ──────────────────────────────────────────────────────────────────
async def run_check_job(check: CheckDefinitionORM):
    started_at = datetime.utcnow()
    try:
        result = await execute_check(check)
        await store_result(check, result, started_at)
        await maybe_trigger_selfheal(check, result)
        log.debug("check.done", name=check.name, status=result["status"])
    except Exception as exc:
        log.error("check.error", name=check.name, error=str(exc))


async def load_checks() -> list:
    async with SessionLocal() as db:
        result = await db.execute(
            select(CheckDefinitionORM).where(CheckDefinitionORM.enabled.is_(True))
        )
        return result.scalars().all()


async def scheduler():
    log.info("worker.started", concurrency=WORKER_CONCURRENCY, environment=ENVIRONMENT)
    next_run: Dict[str, datetime] = {}
    semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)
    tick = 0

    while True:
        checks = await load_checks()
        now = datetime.utcnow()
        tasks = []

        for check in checks:
            cid = str(check.id)
            if cid not in next_run:
                next_run[cid] = now
            if next_run[cid] <= now:
                next_run[cid] = now + timedelta(seconds=check.interval_seconds)

                async def _run(c=check):
                    async with semaphore:
                        await run_check_job(c)

                tasks.append(asyncio.create_task(_run()))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        tick += 1
        if tick % 60 == 0:
            await write_heartbeat()

        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(scheduler())
