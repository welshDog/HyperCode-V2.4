# agents/mission-director/fleet_client.py
"""
Thin httpx client for fleet-controller's existing, unmodified
POST /v1/plans/preview. Fails closed the same way safety_client.py in
agents/fleet-controller does -- any network/parse failure raises
FleetControllerUnavailable, caller maps that to preview_unavailable.
Deliberately no retry logic: a flaky preview call is exactly the kind of
"infrastructure failure, not a plan-quality failure" the spec's error
table already names.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from models import PlanRequest, PlanResponse

_client: Optional[httpx.AsyncClient] = None


class FleetControllerUnavailable(Exception):
    pass


def _url() -> str:
    return (os.getenv("FLEET_CONTROLLER_URL") or "http://fleet-controller:8080").rstrip("/")


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def preview(plan: PlanRequest) -> PlanResponse:
    try:
        resp = await _get_client().post(
            f"{_url()}/v1/plans/preview", json=plan.model_dump(mode="json")
        )
    except Exception as exc:
        raise FleetControllerUnavailable(str(exc)) from exc

    if resp.status_code != 200:
        raise FleetControllerUnavailable(f"fleet-controller returned {resp.status_code}")

    try:
        return PlanResponse(**resp.json())
    except Exception as exc:
        raise FleetControllerUnavailable(f"malformed PlanResponse: {exc}") from exc
