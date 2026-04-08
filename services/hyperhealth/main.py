"""
HyperHealth Orchestrator API
FastAPI-based health-orchestration service for HyperCode V2.0
Port: 8090
"""
import os
import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from models import (
    CheckDefinitionCreate,
    CheckDefinitionOut,
    CheckResultOut,
    HealthReport,
    IncidentOut,
    SelfHealPolicyCreate,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HyperHealth 🧠",
    description="Comprehensive health-orchestration for HyperCode V2.0",
    version="1.0.0",
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hypercode:hypercode@postgres:5432/hypercode")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
HEALER_URL = os.getenv("HEALER_URL", "http://healer-agent:8008")

# ---------------------------------------------------------------------------
# Prometheus metrics registry
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

check_status_gauge = Gauge(
    "hyperhealth_check_status",
    "Check status: 0=OK 1=WARN 2=CRIT",
    ["check_name", "env", "check_type"],
    registry=registry,
)
check_latency_histogram = Histogram(
    "hyperhealth_check_latency_ms",
    "Check execution latency in ms",
    ["check_name", "env"],
    registry=registry,
)
incidents_open_gauge = Gauge(
    "hyperhealth_incidents_open",
    "Number of open incidents by severity",
    ["severity"],
    registry=registry,
)
selfheals_counter = Counter(
    "hyperhealth_selfheals_executed_total",
    "Total self-heal actions executed",
    ["action", "env"],
    registry=registry,
)
selfheals_failed_counter = Counter(
    "hyperhealth_selfheals_failed_total",
    "Total self-heal actions that failed",
    ["action", "env"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# DB / Redis dependencies
# ---------------------------------------------------------------------------
_db_pool: Optional[asyncpg.Pool] = None
_redis: Optional[aioredis.Redis] = None


async def get_db() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _db_pool


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    await get_db()
    await get_redis()
    print("🧠 HyperHealth started — watching everything!")


@app.on_event("shutdown")
async def shutdown():
    if _db_pool:
        await _db_pool.close()
    if _redis:
        await _redis.close()


# ---------------------------------------------------------------------------
# Health / readiness
# ---------------------------------------------------------------------------
@app.get("/health")
async def liveness():
    return {"status": "ok", "service": "hyperhealth", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
async def readiness(db=Depends(get_db), redis=Depends(get_redis)):
    try:
        await db.fetchval("SELECT 1")
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Checks CRUD
# ---------------------------------------------------------------------------
@app.get("/checks", response_model=List[CheckDefinitionOut])
async def list_checks(
    env: Optional[str] = Query(None),
    check_type: Optional[str] = Query(None),
    db=Depends(get_db),
):
    query = "SELECT * FROM check_definitions WHERE enabled = TRUE"
    params = []
    if env:
        params.append(env)
        query += f" AND environment = ${len(params)}"
    if check_type:
        params.append(check_type)
        query += f" AND type = ${len(params)}"
    rows = await db.fetch(query, *params)
    return [dict(r) for r in rows]


@app.post("/checks", response_model=CheckDefinitionOut, status_code=201)
async def create_check(payload: CheckDefinitionCreate, db=Depends(get_db)):
    row = await db.fetchrow(
        """
        INSERT INTO check_definitions
            (id, name, type, target, environment, interval_seconds, thresholds,
             alert_policy_id, self_heal_policy_id, tags, enabled, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,TRUE,NOW())
        RETURNING *
        """,
        uuid4(),
        payload.name,
        payload.type,
        payload.target,
        payload.environment,
        payload.interval_seconds,
        payload.thresholds.model_dump_json(),
        payload.alert_policy_id,
        payload.self_heal_policy_id,
        payload.tags,
    )
    return dict(row)


@app.delete("/checks/{check_id}", status_code=204)
async def delete_check(check_id: UUID, db=Depends(get_db)):
    await db.execute("UPDATE check_definitions SET enabled=FALSE WHERE id=$1", check_id)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@app.get("/results", response_model=List[CheckResultOut])
async def list_results(
    check_id: Optional[UUID] = None,
    env: Optional[str] = None,
    limit: int = Query(50, le=500),
    db=Depends(get_db),
):
    query = "SELECT * FROM check_results"
    filters, params = [], []
    if check_id:
        params.append(check_id)
        filters.append(f"check_id = ${len(params)}")
    if env:
        params.append(env)
        filters.append(f"environment = ${len(params)}")
    if filters:
        query += " WHERE " + " AND ".join(filters)
    params.append(limit)
    query += f" ORDER BY started_at DESC LIMIT ${len(params)}"
    rows = await db.fetch(query, *params)
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Health Report
# ---------------------------------------------------------------------------
@app.get("/health/report", response_model=HealthReport)
async def get_health_report(
    env: str = Query("prod"),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    import json
    cache_key = f"hyperhealth:report:{env}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    total = await db.fetchval(
        "SELECT COUNT(*) FROM check_definitions WHERE environment=$1 AND enabled=TRUE", env
    )
    crit = await db.fetchval(
        """
        SELECT COUNT(DISTINCT cr.check_id)
        FROM check_results cr
        JOIN check_definitions cd ON cd.id = cr.check_id
        WHERE cd.environment=$1
          AND cr.status='CRIT'
          AND cr.started_at > NOW() - INTERVAL '5 minutes'
        """,
        env,
    )
    warn = await db.fetchval(
        """
        SELECT COUNT(DISTINCT cr.check_id)
        FROM check_results cr
        JOIN check_definitions cd ON cd.id = cr.check_id
        WHERE cd.environment=$1
          AND cr.status='WARN'
          AND cr.started_at > NOW() - INTERVAL '5 minutes'
        """,
        env,
    )
    open_incidents = await db.fetch(
        "SELECT * FROM incidents WHERE environment=$1 AND resolved_at IS NULL ORDER BY created_at DESC LIMIT 10",
        env,
    )

    overall = "CRIT" if crit > 0 else ("WARN" if warn > 0 else "OK")
    report = {
        "environment": env,
        "overall_status": overall,
        "total_checks": total or 0,
        "critical_count": crit or 0,
        "warning_count": warn or 0,
        "ok_count": max(0, (total or 0) - (crit or 0) - (warn or 0)),
        "open_incidents": [dict(i) for i in open_incidents],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await redis.setex(cache_key, 30, json.dumps(report, default=str))
    return report


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------
@app.get("/incidents", response_model=List[IncidentOut])
async def list_incidents(
    env: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: bool = False,
    limit: int = Query(20, le=100),
    db=Depends(get_db),
):
    query = "SELECT * FROM incidents"
    filters, params = [], []
    if env:
        params.append(env)
        filters.append(f"environment = ${len(params)}")
    if severity:
        params.append(severity)
        filters.append(f"severity = ${len(params)}")
    if not resolved:
        filters.append("resolved_at IS NULL")
    if filters:
        query += " WHERE " + " AND ".join(filters)
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    rows = await db.fetch(query, *params)
    return [dict(r) for r in rows]


@app.post("/incidents/{incident_id}/resolve", status_code=200)
async def resolve_incident(incident_id: UUID, db=Depends(get_db)):
    await db.execute(
        "UPDATE incidents SET resolved_at=NOW() WHERE id=$1", incident_id
    )
    return {"resolved": True, "id": str(incident_id)}


# ---------------------------------------------------------------------------
# Deployment gate
# ---------------------------------------------------------------------------
@app.get("/gate/{env}")
async def deployment_gate(env: str, db=Depends(get_db)):
    crit_count = await db.fetchval(
        """
        SELECT COUNT(*) FROM incidents
        WHERE environment=$1 AND severity='CRIT' AND resolved_at IS NULL
        """,
        env,
    )
    if crit_count and crit_count > 0:
        raise HTTPException(
            status_code=503,
            detail=f"Deployment blocked: {crit_count} open CRIT incident(s) in {env}",
        )
    return {"gate": "open", "environment": env, "message": "All clear — deploy away! 🚀"}


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return generate_latest(registry)
