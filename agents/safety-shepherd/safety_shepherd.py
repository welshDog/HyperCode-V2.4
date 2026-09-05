"""Safety Shepherd — runtime policy brain between the orchestrator and tool calls (P0-2).

FastAPI service on port 8096. Evaluates proposed agent actions against a
capabilities manifest and returns ALLOW | BLOCK | ESCALATE. ESCALATE raises a
human approval request on the shared `approval_requests` Redis channel (the
dashboard already streams it). Every decision is logged as JSON (Loki scrapes
container stdout) and pushed to a capped Redis list for /safety/events + Grafana.

Endpoints:
  GET  /health         — liveness (unauthenticated)
  POST /evaluate       — decide on a proposed action (X-Agent-Key / X-API-Key)
  GET  /capabilities   — current manifest (unauthenticated, read-only)
  GET  /safety/events  — recent decisions (unauthenticated, read-only)
  GET  /metrics        — Prometheus scrape

Sacred rules honoured: Stripe is exempt (never gated); read-only Docker only;
agents-net + data-net; non-root; 4-space indent.

Redis connection pools:
  Previously every helper opened and closed its own aioredis connection, costing
  ~4 connections per /evaluate call. Under real agent load (30 turns × several
  tool calls each) that exhausts Redis connection slots quickly. Three module-
  level connection pools are now created at startup via the lifespan context and
  closed cleanly on shutdown.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from secrets import compare_digest
from typing import Any, AsyncIterator, Optional

import httpx
import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from policy import ALLOW, BLOCK, ESCALATE, evaluate

# ── logging (structlog JSON → stdout → Loki) ──────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger(agent_name="safety-shepherd")

# ── metrics ───────────────────────────────────────────────────────────────────
safety_decisions_total = Counter(
    "safety_decisions_total",
    "Safety Shepherd decisions",
    ["decision", "category", "agent"],
)
safety_ledger_pushes_total = Counter(
    "safety_ledger_pushes_total",
    "Governance-ledger verdict pushes (HS-P2c)",
    ["status"],
)

# ── config ────────────────────────────────────────────────────────────────────
MANIFEST_PATH = os.getenv("SAFETY_MANIFEST", str(Path(__file__).parent / "capabilities.json"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RATE_WINDOW_SECONDS = int(os.getenv("SAFETY_RATE_WINDOW", "3600"))
EVENTS_KEY = "safety:events"
MAX_STORED_EVENTS = 500
APPROVAL_CHANNEL = "approval_requests"

# HS-P2c — governance-ledger write path (core POST /api/v1/governance/ledger).
# Disabled unless a core agent key is provisioned (mint via scripts/mint_agent_keys.py).
CORE_URL = os.getenv("CORE_URL", "http://hypercode-core:8000").rstrip("/")
LEDGER_PATH = "/api/v1/governance/ledger"

_manifest: dict[str, Any] = {}
_manifest_mtime: float = 0.0


def _swap_db(url: str, db: int) -> str:
    head, sep, tail = url.rpartition("/")
    if sep and tail.isdigit():
        return f"{head}/{db}"
    return f"{url.rstrip('/')}/{db}"


# DB0 = shared approvals channel/keys · DB1 = cache (events) · DB2 = rate limits
CACHE_URL = _swap_db(REDIS_URL, 1)
RATELIMIT_URL = _swap_db(REDIS_URL, 2)

# Module-level connection pools — created at startup, closed at shutdown.
# Each pool is sized for burst traffic (10 connections); redis-py's pool blocks
# rather than raises when exhausted, so peaks are buffered not dropped.
_pool_approvals: Optional[aioredis.Redis] = None
_pool_cache: Optional[aioredis.Redis] = None
_pool_ratelimit: Optional[aioredis.Redis] = None

# Module-level HTTP client for ledger pushes — one client for the process
# lifetime (a per-call AsyncClient costs ~280 ms in TLS/pool setup alone).
_core_client: Optional[httpx.AsyncClient] = None
_ledger_tasks: set[asyncio.Task] = set()


def _make_pool(url: str) -> aioredis.Redis:
    return aioredis.from_url(url, decode_responses=True, max_connections=10)


def _core_agent_key() -> str:
    """Key the Shepherd presents to core (X-Agent-Key, hc_-prefixed)."""
    file_path = os.getenv("CORE_AGENT_KEY_FILE", "")
    if file_path:
        from_file = _read_secret_file(file_path)
        if from_file:
            return from_file
    return (os.getenv("CORE_AGENT_KEY") or "").strip()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Create Redis connection pools on startup; drain them on shutdown."""
    global _pool_approvals, _pool_cache, _pool_ratelimit, _core_client
    _pool_approvals = _make_pool(REDIS_URL)
    _pool_cache = _make_pool(CACHE_URL)
    _pool_ratelimit = _make_pool(RATELIMIT_URL)
    ledger_key = _core_agent_key()
    if ledger_key:
        _core_client = httpx.AsyncClient(
            base_url=CORE_URL, timeout=3.0, headers={"X-Agent-Key": ledger_key}
        )
        log.info("ledger_push_enabled", core=CORE_URL)
    else:
        log.info("ledger_push_disabled", reason="no CORE_AGENT_KEY(_FILE) configured")
    load_manifest(force=True)
    log.info("safety_shepherd_started", port=8096, redis=REDIS_URL)
    try:
        yield
    finally:
        for task in list(_ledger_tasks):
            task.cancel()
        if _core_client is not None:
            await _core_client.aclose()
            _core_client = None
        for pool in (_pool_approvals, _pool_cache, _pool_ratelimit):
            if pool is not None:
                await pool.aclose()
        _pool_approvals = _pool_cache = _pool_ratelimit = None


def _approvals_pool() -> aioredis.Redis:
    if _pool_approvals is None:  # fallback for tests that bypass lifespan
        return _make_pool(REDIS_URL)
    return _pool_approvals


def _cache_pool() -> aioredis.Redis:
    if _pool_cache is None:
        return _make_pool(CACHE_URL)
    return _pool_cache


def _ratelimit_pool() -> aioredis.Redis:
    if _pool_ratelimit is None:
        return _make_pool(RATELIMIT_URL)
    return _pool_ratelimit


app = FastAPI(title="safety-shepherd", version="0.1.0", lifespan=lifespan)


def load_manifest(force: bool = False) -> dict[str, Any]:
    """Load the manifest, hot-reloading when the file changes (no restart needed)."""
    global _manifest, _manifest_mtime
    try:
        mtime = os.path.getmtime(MANIFEST_PATH)
    except OSError:
        return _manifest
    if force or not _manifest or mtime != _manifest_mtime:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            _manifest = json.load(f)
        _manifest_mtime = mtime
        log.info("manifest_loaded", path=MANIFEST_PATH, agents=len(_manifest.get("agents", {})))
    return _manifest


# ── auth (mirrors nemoclaw-agent) ─────────────────────────────────────────────
def _read_secret_file(path: str) -> str:
    # utf-8-sig strips a Windows-editor BOM at read time; UnicodeDecodeError
    # is caught alongside OSError so a non-UTF-8 secret file fails closed
    # (empty string) instead of crashing the request path that calls this.
    # governor's ledger_client.py/main.py mirror this function -- keep them
    # in sync.
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _expected_api_key() -> str:
    file_path = os.getenv("HYPERCODE_API_KEY_FILE") or os.getenv("AGENT_API_KEY_FILE", "")
    if file_path:
        from_file = _read_secret_file(file_path)
        if from_file:
            return from_file
    return (os.getenv("HYPERCODE_API_KEY") or os.getenv("AGENT_API_KEY") or "").strip()


_OPEN_PATHS = ("/health", "/metrics", "/capabilities", "/safety/events")


@app.middleware("http")
async def _agent_auth(request: Request, call_next):
    if request.url.path.startswith(_OPEN_PATHS):
        return await call_next(request)
    expected = _expected_api_key()
    if not expected:
        return JSONResponse(status_code=503, content={"detail": "Agent API key not configured"})
    provided = request.headers.get("x-agent-key") or request.headers.get("x-api-key")
    if not provided or not compare_digest(str(provided), expected):
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# ── models ────────────────────────────────────────────────────────────────────
class EvaluateRequest(BaseModel):
    agent: str = Field(..., description="Requesting agent name")
    category: str = Field("generic", description="docker|http_external|file_write|stripe|discord|generic")
    tool: Optional[str] = Field(None, description="Specific tool/operation name")
    target: Optional[str] = Field(None, description="File path (file_*) or resource id")
    domain: Optional[str] = Field(None, description="Host for http_external/discord/stripe")
    context: dict[str, Any] = Field(default_factory=dict)


# ── redis helpers (now using module-level pools) ──────────────────────────────
async def _action_count(agent: str) -> int:
    window = int(time.time()) // RATE_WINDOW_SECONDS
    key = f"safety:count:{agent}:{window}"
    try:
        val = await _ratelimit_pool().get(key)
        return int(val) if val else 0
    except Exception:
        return 0


async def _bump_action_count(agent: str) -> None:
    window = int(time.time()) // RATE_WINDOW_SECONDS
    key = f"safety:count:{agent}:{window}"
    try:
        async with _ratelimit_pool().pipeline(transaction=False) as pipe:
            pipe.incr(key)
            pipe.expire(key, RATE_WINDOW_SECONDS)
            await pipe.execute()
    except Exception:
        log.warning("rate_count_failed", agent=agent)


async def _record_event(event: dict[str, Any]) -> None:
    try:
        payload = json.dumps(event)
        async with _cache_pool().pipeline(transaction=False) as pipe:
            pipe.lpush(EVENTS_KEY, payload)
            pipe.ltrim(EVENTS_KEY, 0, MAX_STORED_EVENTS - 1)
            await pipe.execute()
    except Exception:
        log.warning("event_record_failed")


async def _push_ledger(event: dict[str, Any]) -> None:
    """Mirror one verdict into core's governance ledger (HS-P2c, fail-soft).

    Never raises; a down core or rejected write costs one warning + a metric
    tick and the decision flow is already complete by the time this runs.
    """
    client = _core_client
    if client is None:
        return
    body = {
        "agent": event.get("agent") or "unknown",
        "action": f"safety.{event.get('category') or 'generic'}",
        "decision": event.get("decision"),
        "tool": event.get("tool"),
        "payload": event,
        "user_id": "system",
    }
    try:
        resp = await client.post(LEDGER_PATH, json=body)
        if resp.status_code >= 400:
            safety_ledger_pushes_total.labels(status="rejected").inc()
            log.warning("ledger_push_rejected", status=resp.status_code, event_id=event.get("id"))
        else:
            safety_ledger_pushes_total.labels(status="ok").inc()
    except Exception:
        safety_ledger_pushes_total.labels(status="error").inc()
        log.warning("ledger_push_failed", event_id=event.get("id"))


def _spawn_ledger_push(event: dict[str, Any]) -> None:
    """Fire-and-forget ledger push so /evaluate latency stays flat."""
    if _core_client is None:
        return
    task = asyncio.create_task(_push_ledger(event))
    _ledger_tasks.add(task)
    task.add_done_callback(_ledger_tasks.discard)


async def _raise_approval(event: dict[str, Any]) -> str:
    """Create a human approval request on the shared channel (dashboard streams it)."""
    approval_id = str(uuid.uuid4())
    request = {
        "id": approval_id,
        "agent": event.get("agent"),
        "action_type": event.get("category"),
        "source": "safety-shepherd",
        "details": event,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        r = _approvals_pool()
        await r.set(f"approval:{approval_id}", json.dumps(request), ex=900)
        await r.sadd("approval:pending", approval_id)
        await r.publish(APPROVAL_CHANNEL, json.dumps(request))
    except Exception:
        log.warning("approval_publish_failed", approval_id=approval_id)
    return approval_id


# ── routes ────────────────────────────────────────────────────────────────────
@app.post("/evaluate")
async def evaluate_action(body: EvaluateRequest) -> dict[str, Any]:
    manifest = load_manifest()
    count = await _action_count(body.agent)
    decision = evaluate(manifest, body.model_dump(), action_count=count)

    event = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": body.agent,
        "category": body.category,
        "tool": body.tool,
        "target": body.target,
        "domain": body.domain,
        "decision": decision.decision,
        "reason": decision.reason,
        "rule": decision.rule,
    }

    approval_id: Optional[str] = None
    if decision.decision == ESCALATE:
        approval_id = await _raise_approval(event)
        event["approval_id"] = approval_id
    elif decision.decision == ALLOW:
        await _bump_action_count(body.agent)

    safety_decisions_total.labels(
        decision=decision.decision, category=body.category, agent=body.agent
    ).inc()
    await _record_event(event)
    _spawn_ledger_push(event)
    log.info("decision", **event)

    result = decision.as_dict()
    result["event_id"] = event["id"]
    if approval_id:
        result["approval_id"] = approval_id
    return result


@app.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    return load_manifest()


@app.get("/safety/events")
async def safety_events(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(MAX_STORED_EVENTS, limit))
    events: list[dict[str, Any]] = []
    try:
        raw = await _cache_pool().lrange(EVENTS_KEY, 0, limit - 1)
        events = [json.loads(x) for x in raw]
    except Exception:
        log.warning("events_read_failed")
    return {"count": len(events), "events": events}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health() -> dict[str, Any]:
    manifest = load_manifest()
    return {
        "status": "ok",
        "service": "safety-shepherd",
        "manifest_agents": len(manifest.get("agents", {})),
        "api_key_configured": bool(_expected_api_key()),
        "ledger_push_enabled": _core_client is not None,
        "rate_window_seconds": RATE_WINDOW_SECONDS,
    }
