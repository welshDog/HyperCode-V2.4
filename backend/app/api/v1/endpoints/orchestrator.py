from __future__ import annotations

from typing import Any

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import httpx
import redis.asyncio as redis

from app.api import deps
from app.core.config import settings
from app.db.session import get_db


router = APIRouter()


def _orchestrator_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.ORCHESTRATOR_API_KEY:
        headers["X-API-Key"] = settings.ORCHESTRATOR_API_KEY
    return headers


@router.get("/agents")
async def get_agents(current_user: Any = Depends(deps.get_current_active_user)) -> Any:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ORCHESTRATOR_URL}/agents", headers=_orchestrator_headers())
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


@router.get("/system/health")
async def get_system_health(current_user: Any = Depends(deps.get_current_active_user)) -> Any:
    last_checked = datetime.now(timezone.utc).isoformat()
    services: dict[str, Any] = {}

    # FIX 1: Guard — skip Docker entirely if proxy URL is not configured (e.g. lean mode)
    docker_proxy_url = getattr(settings, "DOCKER_SOCKET_PROXY_URL", None)

    # FIX 2: Single shared httpx client for both upstream calls
    async with httpx.AsyncClient(timeout=10.0) as client:

        # --- Docker socket proxy (optional) ---
        if docker_proxy_url:
            try:
                resp = await client.get(f"{docker_proxy_url}/containers/json?all=1")
                if resp.status_code == 200:
                    payload = resp.json()
                    if isinstance(payload, list):
                        for item in payload:
                            if not isinstance(item, dict):
                                continue
                            names = item.get("Names")
                            name = None
                            if isinstance(names, list) and names:
                                raw = names[0]
                                if isinstance(raw, str):
                                    name = raw.lstrip("/")
                            if not name:
                                raw_name = item.get("Name")
                                if isinstance(raw_name, str):
                                    name = raw_name.lstrip("/")
                            if not name:
                                continue

                            state = item.get("State")
                            status_text = item.get("Status")
                            status_raw = f"{status_text or ''} {state or ''}".lower()

                            # FIX 3: Handle transitional states — don't show as red/DOWN
                            if "unhealthy" in status_raw or (
                                isinstance(state, str) and state.lower() in {"exited", "dead"}
                            ):
                                status = "down"
                            elif "healthy" in status_raw or (
                                isinstance(state, str) and state.lower() == "running"
                            ):
                                status = "healthy"
                            elif isinstance(state, str) and state.lower() in {
                                "restarting", "created", "paused"
                            }:
                                # FIX 3: Transitional — show as starting, not down
                                status = "starting"
                            else:
                                status = "unknown"

                            services[name] = {
                                "status": status,
                                "latency_ms": None,
                                "last_checked": last_checked,
                                "error": None,
                            }
            except Exception as e:
                services["docker"] = {
                    "status": "degraded",
                    "latency_ms": None,
                    "last_checked": last_checked,
                    "error": str(e),
                }

        # --- Crew-orchestrator health overlay ---
        # FIX 4: Reduced to 3s timeout — prevents hanging during lean mode startup
        try:
            resp = await client.get(
                f"{settings.ORCHESTRATOR_URL}/system/health",
                headers=_orchestrator_headers(),
                timeout=3.0,
            )
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, dict):
                    maybe_services = (
                        payload.get("services")
                        if isinstance(payload.get("services"), dict)
                        else payload
                    )
                    if isinstance(maybe_services, dict):
                        for name, info in maybe_services.items():
                            if not isinstance(name, str) or not name:
                                continue
                            info_obj = info if isinstance(info, dict) else {"status": str(info)}
                            status = info_obj.get("status")
                            if isinstance(status, str):
                                status_str = status
                            elif isinstance(status, bool):
                                status_str = "healthy" if status else "down"
                            else:
                                status_str = "unknown"

                            services[name] = {
                                "status": status_str,
                                "latency_ms": info_obj.get("latency_ms"),
                                "last_checked": info_obj.get("last_checked") or last_checked,
                                "error": info_obj.get("error"),
                            }
        except Exception:
            pass

    return services


@router.post("/execute")
async def execute_task(payload: dict, current_user: Any = Depends(deps.get_current_active_user)) -> Any:
    """Proxy task execution through Core API → crew-orchestrator.
    Adds the authenticated user_id so downstream services can award BROski$.
    """
    payload.setdefault("user_id", current_user.id)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.ORCHESTRATOR_URL}/execute",
                headers={**_orchestrator_headers(), "Content-Type": "application/json"},
                json=payload,
            )
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {e}")


@router.post("/approvals/respond")
async def approvals_respond(payload: dict, current_user: Any = Depends(deps.get_current_active_user)) -> Any:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ORCHESTRATOR_URL}/approvals/respond",
                headers={**_orchestrator_headers(), "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code != 200:
            return {"status": "error", "detail": resp.text}
        return resp.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.websocket("/ws/approvals")
async def approvals_ws(websocket: WebSocket, token: str | None = None, db: Session = Depends(get_db)):
    if token is None:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4401)
        return

    try:
        deps.get_current_user(db=db, token=token)
    except Exception:
        await websocket.close(code=4403)
        return

    await websocket.accept()

    r = await redis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("approval_requests")

    try:
        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if data is None:
                continue
            await websocket.send_text(data)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await pubsub.unsubscribe("approval_requests")
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass
        try:
            await r.close()
        except Exception:
            pass
