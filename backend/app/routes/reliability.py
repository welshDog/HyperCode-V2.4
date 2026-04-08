"""
Tasks 7 & 8 — Reliability / Error Budget + System State
Provides:
  GET /api/v1/error-budget  — SLO error budget calculation
  GET /api/v1/system/state  — aggregate stable/watch/on_fire health state

SLO definition (hardcoded baseline, configurable via env vars):
  Target error rate: <= 1%   (SLO_ERROR_RATE_TARGET, default 1.0)
  Measurement window: last 5 minutes of Redis req/error_count keys

Budget logic:
  - allowed_errors = req_total * (slo_target / 100)
  - budget_remaining = allowed_errors - actual_errors
  - budget_pct = 100 * (budget_remaining / allowed_errors) if allowed_errors > 0 else 100
  - gate: "ok" if budget_pct >= 20, "warning" if >= 0, "exhausted" if < 0

Redis keys consumed (written by Task 10 HTTP middleware):
  req_count:{YYYYMMHHMM}    — per-minute request count
  error_count:{YYYYMMHHMM}  — per-minute error count (4xx/5xx)
"""

import datetime
import os
from typing import List

import redis.asyncio as aioredis
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

SLO_TARGET_PCT: float = float(os.getenv("SLO_ERROR_RATE_TARGET", "1.0"))
WINDOW_MINUTES: int   = 5


class ErrorBudget(BaseModel):
    sloTargetPct: float       # e.g. 1.0 = 1% error rate SLO
    windowMinutes: int        # measurement window
    requestTotal: int         # total requests in window
    errorTotal: int           # total errors in window
    actualErrorPct: float     # actual error rate in window
    allowedErrors: float      # how many errors the SLO permits
    budgetRemaining: float    # allowed - actual (negative = overspent)
    budgetPct: float          # percentage of budget remaining (100 = full, 0 = exhausted)
    gate: str                 # "ok" | "warning" | "exhausted"
    collectedAt: str


class SystemState(BaseModel):
    state: str         # "stable" | "watch" | "on_fire"
    reasons: List[str] # human-readable list of triggered conditions
    errorBudget: ErrorBudget
    collectedAt: str


@router.get("/system/state", response_model=SystemState)
async def get_system_state() -> SystemState:
    """
    Computes aggregate system health state from error budget + agent heartbeats.

    States:
      stable   — budget > 20%, all conditions green
      watch    — budget 0–20% OR any warning-level condition
      on_fire  — budget exhausted (< 0%) OR error rate > 5%
    """
    budget = await get_error_budget()
    reasons: List[str] = []

    if budget.gate == "exhausted":
        reasons.append(f"Error budget exhausted ({budget.budgetPct:.1f}% remaining)")
    elif budget.gate == "warning":
        reasons.append(f"Error budget low ({budget.budgetPct:.1f}% remaining)")

    if budget.actualErrorPct > 5.0:
        reasons.append(f"Error rate critical: {budget.actualErrorPct:.2f}% (threshold 5%)")

    if budget.gate == "exhausted" or budget.actualErrorPct > 5.0:
        state = "on_fire"
    elif budget.gate == "warning":
        state = "watch"
    else:
        state = "stable"

    return SystemState(
        state=state,
        reasons=reasons,
        errorBudget=budget,
        collectedAt=budget.collectedAt,
    )


@router.get("/error-budget", response_model=ErrorBudget)
async def get_error_budget() -> ErrorBudget:
    """
    Computes the SLO error budget for the last N minutes.
    Returns a gate value that can block deployments or trigger alerts.
    """
    now = datetime.datetime.utcnow()
    minute_keys: List[str] = []
    for i in range(WINDOW_MINUTES):
        ts = now - datetime.timedelta(minutes=i)
        minute_keys.append(ts.strftime("%Y%m%d%H%M"))

    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        async with r.pipeline(transaction=False) as pipe:
            for key in minute_keys:
                pipe.get(f"req_count:{key}")
            for key in minute_keys:
                pipe.get(f"error_count:{key}")
            results = await pipe.execute()
    finally:
        await r.aclose()

    req_counts   = results[:WINDOW_MINUTES]
    error_counts = results[WINDOW_MINUTES:]

    req_total   = sum(int(v or 0) for v in req_counts)
    error_total = sum(int(v or 0) for v in error_counts)

    actual_error_pct = round((error_total / req_total * 100) if req_total > 0 else 0.0, 3)
    allowed_errors   = req_total * (SLO_TARGET_PCT / 100)
    budget_remaining = round(allowed_errors - error_total, 2)
    budget_pct       = round((budget_remaining / allowed_errors * 100) if allowed_errors > 0 else 100.0, 1)

    if budget_pct >= 20:
        gate = "ok"
    elif budget_pct >= 0:
        gate = "warning"
    else:
        gate = "exhausted"

    return ErrorBudget(
        sloTargetPct=SLO_TARGET_PCT,
        windowMinutes=WINDOW_MINUTES,
        requestTotal=req_total,
        errorTotal=error_total,
        actualErrorPct=actual_error_pct,
        allowedErrors=allowed_errors,
        budgetRemaining=budget_remaining,
        budgetPct=budget_pct,
        gate=gate,
        collectedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
