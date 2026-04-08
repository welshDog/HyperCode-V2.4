from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
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
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ORCHESTRATOR_URL}/system/health", headers=_orchestrator_headers())
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


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

