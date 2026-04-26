from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api import deps
from app.models import models

router = APIRouter()


class SplitRequest(BaseModel):
    task: str = Field(min_length=1, max_length=10_000)
    max_microtasks: int = Field(default=5, ge=3, le=7)


@router.post("", response_model=dict[str, Any])
async def hypersplit(
    req: SplitRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    agent_base_url = os.getenv("HYPER_SPLIT_AGENT_URL", "http://hyper-split-agent:8096").rstrip("/")
    timeout = httpx.Timeout(35.0, connect=5.0)
    transport = httpx.AsyncHTTPTransport(retries=2)

    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            resp = await client.post(f"{agent_base_url}/split", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"HyperSplit agent error ({status}): {detail}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"HyperSplit agent unreachable: {exc}")
