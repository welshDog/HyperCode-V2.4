"""Reverse-proxy routes that forward `/api/v1/skills-synth/*` to the
SkillWeaver agent-side registry (container DNS: http://skillweaver:8051).

Why a dedicated prefix (`skills-synth`) instead of piggy-backing on the
existing `/skills` router? That router already owns
`POST /api/v1/skills/search` for the SKILL.md catalog search — combining
the two would be a footgun (the synthesis registry returns JSON shape
`{"count", "skills":[...]}` while the catalog search returns
`{"matches", "usedFallback", "error"}`). Keeping them separate keeps the
two systems independently evolvable and trivially traceable in logs.

Fail-soft by design (same philosophy as the skills catalog search):
*   If SkillWeaver is unreachable / timing out we return HTTP 503 with a
    stable error body — never a raw 5xx traceback to the caller.
*   The proxy is lazy: no connection pool is held for SkillWeaver unless
    a call actually comes in, so a missing SkillWeaver container has
    zero startup-time impact on `hypercode-core`.
*   Any 4xx/5xx response from SkillWeaver is forwarded verbatim so
    clients can still distinguish 400 (bad request) from 503 (unreachable).
*   Uses plain forwarding of method, query params, body, Content-Type,
    no transformation — the `X-Forwarded-*` headers are added so the
    synthesis engine can tell the call came through core if it needs to.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills-synthesis"])

_PROXY_PREFIX = "/api/v1/skills-synth"


def _upstream_base() -> str:
    """The SkillWeaver server base URL. Configurable via env so local-dev
    can point to a non-standard port, and the default matches the Docker
    Compose service DNS on `agents-net`."""
    settings = get_settings()
    value = getattr(settings, "SKILLWEAVER_URL", None)
    if isinstance(value, str) and value:
        return value.rstrip("/")
    return "http://skillweaver:8051"


async def _proxy(
    method: str,
    path: str,
    *,
    query_params: Optional[dict] = None,
    body: Optional[bytes] = None,
    content_type: Optional[str] = None,
    request_timeout: float = 15.0,
) -> tuple[int, bytes, str | None]:
    """Perform the actual upstream call. Returns (status_code, body_bytes,
    response_content_type)."""
    upstream = _upstream_base()
    url = f"{upstream}{path}"
    headers: dict[str, str] = {}
    if content_type:
        headers["Content-Type"] = content_type
    headers["X-Forwarded-For"] = "hypercode-core"
    headers["X-Forwarded-Proto"] = "http"

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            resp = await client.request(
                method,
                url,
                params=query_params or {},
                content=body,
                headers=headers,
            )
    except httpx.ConnectError as exc:
        logger.warning("SkillWeaver proxy: upstream unreachable (%s)", exc)
        raise HTTPException(
            status_code=503,
            detail="SkillWeaver synthesis service is unreachable",
        )
    except httpx.TimeoutException as exc:
        logger.warning("SkillWeaver proxy: upstream timed out (%s)", exc)
        raise HTTPException(
            status_code=504,
            detail="SkillWeaver synthesis service timed out",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("SkillWeaver proxy: unexpected error calling upstream")
        raise HTTPException(
            status_code=502,
            detail=f"SkillWeaver proxy error: {exc!r}",
        )

    return resp.status_code, resp.content, resp.headers.get("Content-Type")


@router.get("")
async def list_skills_proxy(
    request: Request,
    agent_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
) -> Response:
    """GET /api/v1/skills-synth -> forward to SkillWeaver /api/v1/skills/list
    with optional agent_id/category filters."""
    params: dict[str, Any] = {}
    if agent_id:
        params["agent_id"] = agent_id
    if category:
        params["category"] = category
    status, body, ct = await _proxy("GET", "/api/v1/skills/list", query_params=params)
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.get("/stats")
async def stats_proxy(request: Request) -> Response:
    status, body, ct = await _proxy("GET", "/api/v1/stats")
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.get("/health")
async def health_proxy(request: Request) -> Response:
    status, body, ct = await _proxy("GET", "/health")
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.get("/compositions/history")
async def compositions_history_proxy(
    request: Request, limit: int = Query(default=10, ge=1),
) -> Response:
    status, body, ct = await _proxy(
        "GET", "/api/v1/compositions/history", query_params={"limit": limit},
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.get("/{skill_id}")
async def get_skill_proxy(request: Request, skill_id: str) -> Response:
    status, body, ct = await _proxy("GET", f"/api/v1/skills/{skill_id}")
    if status == 404:
        raise HTTPException(status_code=404, detail=body.decode(errors="replace") or f"Skill {skill_id!r} not found")
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.post("/register")
async def register_skill_proxy(request: Request) -> Response:
    raw = await request.body()
    status, body, ct = await _proxy(
        "POST", "/api/v1/skills/register",
        body=raw, content_type=request.headers.get("Content-Type"),
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.post("/register_batch")
async def register_skill_batch_proxy(request: Request) -> Response:
    raw = await request.body()
    status, body, ct = await _proxy(
        "POST", "/api/v1/skills/register_batch",
        body=raw, content_type=request.headers.get("Content-Type"),
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.post("/discover")
async def discover_skills_proxy(request: Request) -> Response:
    raw = await request.body()
    status, body, ct = await _proxy(
        "POST", "/api/v1/skills/discover",
        body=raw, content_type=request.headers.get("Content-Type"),
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.post("/compose")
async def compose_skills_proxy(request: Request) -> Response:
    raw = await request.body()
    status, body, ct = await _proxy(
        "POST", "/api/v1/skills/compose",
        body=raw, content_type=request.headers.get("Content-Type"),
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")


@router.delete("/agent/{agent_id}")
async def deregister_agent_proxy(request: Request, agent_id: str) -> Response:
    status, body, ct = await _proxy(
        "DELETE", f"/api/v1/skills/agent/{agent_id}",
    )
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.decode(errors="replace"))
    return Response(content=body, status_code=status, media_type=ct or "application/json")
