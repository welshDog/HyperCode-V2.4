"""
HyperHealth Orchestrator API — v1.1
Added: PATCH /checks/{id} for in-place updates (used by seed --force)
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, update

from models import (
    Base,
    CheckDefinitionORM, CheckResultORM,
    CheckDefinitionCreate, CheckDefinitionOut, CheckResultOut, HealthReportOut
)

# ── Logging ────────────────────────────────────────────────────────────────────
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

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable must be set")

ASYNC_DB_URL = (
    DATABASE_URL
    if "asyncpg" in DATABASE_URL
    else DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
)

API_KEY     = os.environ.get("API_KEY", "")
REDIS_URL   = os.environ.get("REDIS_URL", "redis://redis:6379/0")
HEALER_URL  = os.environ.get("HEALER_URL", "http://healer-agent:8008")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

if not API_KEY:
    raise RuntimeError("API_KEY environment variable must be set")

# ── Prometheus ──────────────────────────────────────────────────────────────────
REGISTRY = CollectorRegistry(auto_describe=False)
CHECK_STATUS    = Gauge("hyperhealth_check_status",    "Check status 0=OK 1=WARN 2=CRIT",  ["check_name","environment","type"],  registry=REGISTRY)
CHECK_LATENCY   = Histogram("hyperhealth_check_latency_ms", "Check latency ms", ["check_name","type"], buckets=[10,50,100,250,500,1000,2500,5000], registry=REGISTRY)
INCIDENTS_OPEN  = Gauge("hyperhealth_incidents_open",  "Open incidents",              ["severity","environment"],             registry=REGISTRY)
SELFHEALS_TOTAL = Counter("hyperhealth_selfheals_executed_total", "Self-heals run",  ["action","service"],                   registry=REGISTRY)
SELFHEALS_FAIL  = Counter("hyperhealth_selfheals_failed_total",   "Self-heals failed",["action","service"],                   registry=REGISTRY)

# ── DB ───────────────────────────────────────────────────────────────────────────
engine = create_async_engine(ASYNC_DB_URL, pool_size=10, max_overflow=20, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("hyperhealth.startup", environment=ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("hyperhealth.db_ready")
    await _ping_healer()
    yield
    await engine.dispose()
    log.info("hyperhealth.shutdown")


async def _ping_healer():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{HEALER_URL}/health")
            log.info("healer.ping", status=r.status_code)
    except Exception as e:
        log.warning("healer.unreachable", error=str(e))


app = FastAPI(title="HyperHealth", version="1.1.0", lifespan=lifespan)


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# ── Routes ───────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hyperhealth", "version": "1.1.0",
            "environment": ENVIRONMENT, "timestamp": datetime.utcnow().isoformat()}


@app.get("/checks", response_model=List[CheckDefinitionOut])
async def list_checks(
    environment: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    stmt = select(CheckDefinitionORM)
    if environment:
        stmt = stmt.where(CheckDefinitionORM.environment == environment)
    if enabled_only:
        stmt = stmt.where(CheckDefinitionORM.enabled.is_(True))
    return (await db.execute(stmt)).scalars().all()


@app.post("/checks", response_model=CheckDefinitionOut, status_code=201)
async def create_check(
    payload: CheckDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    check = CheckDefinitionORM(
        id=uuid.uuid4(), name=payload.name, type=payload.type,
        target=payload.target, environment=payload.environment,
        interval_seconds=payload.interval_seconds,
        thresholds={k: v.model_dump() for k, v in payload.thresholds.items()},
        alert_policy_id=payload.alert_policy_id,
        self_heal_policy_id=payload.self_heal_policy_id,
        tags=payload.tags, enabled=payload.enabled,
    )
    db.add(check)
    await db.commit()
    await db.refresh(check)
    log.info("check.created", name=check.name, type=check.type)
    return check


@app.get("/checks/{check_id}", response_model=CheckDefinitionOut)
async def get_check(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(CheckDefinitionORM).where(CheckDefinitionORM.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    return check


@app.patch("/checks/{check_id}", response_model=CheckDefinitionOut)
async def update_check(
    check_id: uuid.UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Partially update a check definition in-place. Used by seed --force."""
    result = await db.execute(select(CheckDefinitionORM).where(CheckDefinitionORM.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    allowed = {"target", "interval_seconds", "thresholds", "tags", "enabled",
               "environment", "alert_policy_id", "self_heal_policy_id"}
    for field, value in payload.items():
        if field in allowed:
            # thresholds come in as raw dicts from seed — store as-is
            setattr(check, field, value)

    check.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(check)
    log.info("check.updated", check_id=str(check_id), fields=list(payload.keys()))
    return check


@app.delete("/checks/{check_id}", status_code=204)
async def delete_check(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(CheckDefinitionORM).where(CheckDefinitionORM.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    check.enabled = False
    await db.commit()


@app.get("/checks/{check_id}/results", response_model=List[CheckResultOut])
async def get_check_results(
    check_id: uuid.UUID,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    stmt = (
        select(CheckResultORM)
        .where(CheckResultORM.check_id == check_id)
        .order_by(CheckResultORM.started_at.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


@app.get("/health/report", response_model=HealthReportOut)
async def get_health_report(
    env: str = Query(default="prod"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    since = datetime.utcnow() - timedelta(minutes=10)
    rows = (await db.execute(
        select(CheckResultORM.status, func.count(CheckResultORM.id))
        .where(CheckResultORM.environment == env, CheckResultORM.started_at >= since)
        .group_by(CheckResultORM.status)
    )).all()
    status_counts = {r[0]: r[1] for r in rows}
    total = sum(status_counts.values())
    overall = "CRIT" if status_counts.get("CRIT", 0) > 0 else "WARN" if status_counts.get("WARN", 0) > 0 else "OK"

    crits = (await db.execute(
        select(CheckResultORM)
        .where(CheckResultORM.environment == env, CheckResultORM.status == "CRIT",
               CheckResultORM.started_at >= since)
        .order_by(CheckResultORM.started_at.desc()).limit(5)
    )).scalars().all()

    recommendations = []
    if status_counts.get("CRIT", 0):  recommendations.append("Investigate CRIT checks — self-heal may be triggered")
    if status_counts.get("WARN", 0) > 2: recommendations.append("Multiple WARNs — review thresholds or capacity")
    if total == 0: recommendations.append("No results in last 10 min — are workers running?")

    return HealthReportOut(
        environment=env, generated_at=datetime.utcnow(),
        total_checks=total, status_counts=status_counts, overall_status=overall,
        top_incidents=[{"check_id": str(c.check_id), "message": c.message, "at": c.started_at.isoformat()} for c in crits],
        self_heals_last_hour=0, mttr_seconds=None, recommendations=recommendations,
    )


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(REGISTRY).decode(), media_type=CONTENT_TYPE_LATEST)


@app.post("/selfheal/trigger")
async def trigger_selfheal(
    service: str = Query(...),
    action: str = Query(default="restart"),
    env: str = Query(default="prod"),
    _: str = Depends(verify_api_key),
):
    import httpx
    payload = {"agent_name": service, "action": action, "environment": env, "source": "hyperhealth-manual"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(f"{HEALER_URL}/heal", json=payload)
            r.raise_for_status()
            SELFHEALS_TOTAL.labels(action=action, service=service).inc()
            return {"status": "triggered", "service": service, "healer_response": r.json()}
    except Exception as exc:
        SELFHEALS_FAIL.labels(action=action, service=service).inc()
        raise HTTPException(status_code=502, detail=f"Healer unreachable: {exc}")
