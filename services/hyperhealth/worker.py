"""
HyperHealth Async Worker
Runs all health checks concurrently, stores results, triggers self-healing.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
import asyncpg
import httpx
import redis.asyncio as aioredis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hypercode:hypercode@postgres:5432/hypercode")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
HEALER_URL = os.getenv("HEALER_URL", "http://healer-agent:8008")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "200"))

# Track consecutive failures per check for self-heal trigger
_failure_counts: Dict[str, int] = {}
_last_heal: Dict[str, datetime] = {}

SELF_HEAL_THRESHOLD = 3       # CRIT failures before auto-heal
SELF_HEAL_COOLDOWN_MINS = 5   # minutes between heals per service


# ---------------------------------------------------------------------------
# DB / Redis helpers
# ---------------------------------------------------------------------------
async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=20)


async def get_redis() -> aioredis.Redis:
    return await aioredis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Check executors
# ---------------------------------------------------------------------------
async def execute_http_check(target: str, timeout: float = 5.0) -> Dict[str, Any]:
    start = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(target)
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        ok = resp.status_code < 400
        return {
            "status": "OK" if ok else "CRIT",
            "latency_ms": round(latency, 2),
            "value": resp.status_code,
            "message": f"HTTP {resp.status_code}",
        }
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {"status": "CRIT", "latency_ms": round(latency, 2), "value": 0, "message": str(e)}


async def execute_db_check(dsn: str, timeout: float = 5.0) -> Dict[str, Any]:
    start = datetime.now(timezone.utc)
    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=timeout)
        await conn.fetchval("SELECT 1")
        await conn.close()
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {"status": "OK", "latency_ms": round(latency, 2), "value": 1, "message": "SELECT 1 OK"}
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {"status": "CRIT", "latency_ms": round(latency, 2), "value": 0, "message": str(e)}


async def execute_redis_check(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    start = datetime.now(timezone.utc)
    try:
        r = await asyncio.wait_for(aioredis.from_url(url, decode_responses=True), timeout=timeout)
        await r.ping()
        await r.close()
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {"status": "OK", "latency_ms": round(latency, 2), "value": 1, "message": "PONG"}
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {"status": "CRIT", "latency_ms": round(latency, 2), "value": 0, "message": str(e)}


async def execute_check(check: Dict[str, Any]) -> Dict[str, Any]:
    check_type = check["type"]
    target = check["target"]
    if check_type == "http":
        return await execute_http_check(target)
    elif check_type == "db":
        return await execute_db_check(target)
    elif check_type == "cache":
        return await execute_redis_check(target)
    else:
        # Generic HTTP fallback for unknown types
        return await execute_http_check(target)


# ---------------------------------------------------------------------------
# Store result + push metrics
# ---------------------------------------------------------------------------
async def store_result(pool: asyncpg.Pool, check: Dict, result: Dict):
    await pool.execute(
        """
        INSERT INTO check_results
            (id, check_id, status, latency_ms, value, message, environment, started_at, finished_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
        """,
        uuid4(),
        check["id"],
        result["status"],
        result["latency_ms"],
        str(result["value"]),
        result["message"],
        check["environment"],
    )


# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------
async def send_slack_alert(check: Dict, result: Dict):
    if not SLACK_WEBHOOK:
        return
    payload = {
        "text": (
            f"🚨 *[{result['status']}]* `{check['name']}` ({check['environment']})\n"
            f"Target: {check['target']}\n"
            f"Message: {result['message']}\n"
            f"Latency: {result['latency_ms']}ms"
        )
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(SLACK_WEBHOOK, json=payload)
    except Exception as e:
        print(f"Slack alert failed: {e}")


# ---------------------------------------------------------------------------
# Self-healing
# ---------------------------------------------------------------------------
async def maybe_self_heal(check: Dict, result: Dict):
    check_id = str(check["id"])
    name = check["name"]
    env = check["environment"]

    if result["status"] == "CRIT":
        _failure_counts[check_id] = _failure_counts.get(check_id, 0) + 1
    else:
        _failure_counts[check_id] = 0
        return

    if _failure_counts[check_id] < SELF_HEAL_THRESHOLD:
        return

    # Check cooldown
    last = _last_heal.get(check_id)
    if last and (datetime.now(timezone.utc) - last) < timedelta(minutes=SELF_HEAL_COOLDOWN_MINS):
        return

    # Call Healer Agent
    _last_heal[check_id] = datetime.now(timezone.utc)
    _failure_counts[check_id] = 0
    print(f"🩹 Self-heal triggered for {name} ({env})")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{HEALER_URL}/heal",
                json={"service": name, "environment": env, "reason": result["message"]},
            )
        print(f"✅ Healer called for {name}")
        await send_slack_alert(check, {
            **result,
            "message": f"🩹 Auto-heal triggered for {name} after {SELF_HEAL_THRESHOLD} CRITs"
        })
    except Exception as e:
        print(f"❌ Self-heal failed for {name}: {e}")


# ---------------------------------------------------------------------------
# Main check runner
# ---------------------------------------------------------------------------
async def run_check(pool: asyncpg.Pool, check: Dict):
    try:
        result = await execute_check(check)
        await store_result(pool, check, result)
        if result["status"] in ("CRIT", "WARN"):
            await send_slack_alert(check, result)
        await maybe_self_heal(check, result)
        status_icon = "✅" if result["status"] == "OK" else ("⚠️" if result["status"] == "WARN" else "🚨")
        print(f"{status_icon} [{check['environment']}] {check['name']}: {result['status']} ({result['latency_ms']}ms)")
    except Exception as e:
        print(f"❌ Check {check['name']} crashed: {e}")


# ---------------------------------------------------------------------------
# Scheduler loop
# ---------------------------------------------------------------------------
async def scheduler():
    print("🚀 HyperHealth Worker starting...")
    pool = await get_pool()
    next_run: Dict[str, datetime] = {}
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def bounded_check(check):
        async with semaphore:
            await run_check(pool, check)

    print("✅ DB connected — entering check loop")

    while True:
        try:
            checks = await pool.fetch(
                "SELECT * FROM check_definitions WHERE enabled = TRUE"
            )
            now = datetime.now(timezone.utc)
            tasks = []
            for check in checks:
                cid = str(check["id"])
                if next_run.get(cid, datetime.min.replace(tzinfo=timezone.utc)) <= now:
                    tasks.append(asyncio.create_task(bounded_check(dict(check))))
                    next_run[cid] = now + timedelta(seconds=check["interval_seconds"])

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            print(f"⚠️ Scheduler error: {e}")

        await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(scheduler())
