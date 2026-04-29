from __future__ import annotations

import hmac
import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import models
from app.models.pets import PetProvisionEvent
from app.services import broski_service

logger = logging.getLogger(__name__)

router = APIRouter()


class PetProvisionRequest(BaseModel):
    source_id: str = Field(..., max_length=128)
    discord_id: str = Field(..., max_length=32)
    course_modules_completed: int = Field(default=0, ge=0, le=10_000)


class PetProvisionResponse(BaseModel):
    pet_id: str
    name: str
    species: str
    rarity: str
    message: str


class PetFeedRequest(BaseModel):
    discord_id: str = Field(..., max_length=32)


class PetFeedResponse(BaseModel):
    discord_id: str
    hunger: int
    energy: int
    happiness: int


def _verify_shop_secret(x_sync_secret: str = Header(..., alias="X-Sync-Secret")) -> None:
    expected = settings.SHOP_SYNC_SECRET
    if not expected:
        raise HTTPException(status_code=503, detail="SHOP_SYNC_SECRET not configured — pet mint disabled")
    if not hmac.compare_digest(x_sync_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid sync secret")


def _pets_bridge_base_url() -> str:
    return (getattr(settings, "PETS_BRIDGE_URL", None) or "http://broski-pets-bridge:8098").rstrip("/")

def _pets_bridge_auth_headers() -> dict[str, str]:
    api_key = (getattr(settings, "API_KEY", None) or "").strip()
    if not api_key:
        return {}
    return {"x-api-key": api_key}


async def _pets_bridge_get(path: str, timeout_s: float = 6.0) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        return await client.get(_pets_bridge_base_url() + path, headers=_pets_bridge_auth_headers())


async def _pets_bridge_post(path: str, json_body: dict[str, Any], timeout_s: float = 10.0) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        return await client.post(
            _pets_bridge_base_url() + path,
            json=json_body,
            headers=_pets_bridge_auth_headers(),
        )


@router.post("/provision", response_model=PetProvisionResponse)
async def provision_pet(
    payload: PetProvisionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_shop_secret),
) -> Any:
    existing = db.query(PetProvisionEvent).filter(PetProvisionEvent.source_id == payload.source_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="source_id already processed — no double mint")

    user = db.query(models.User).filter(models.User.discord_id == payload.discord_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No V2.4 user linked to that Discord ID")

    try:
        status_resp = await _pets_bridge_get(f"/pet/{payload.discord_id}/status", timeout_s=3.0)
        if status_resp.status_code == 200:
            raise HTTPException(status_code=409, detail="Pet already exists for this Discord ID")
    except HTTPException:
        raise
    except Exception:
        pass

    try:
        broski_service.spend_coins(user_id=user.id, amount=300, reason="Mint BROskiPet", db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        provision_resp = await _pets_bridge_post(
            "/provision",
            {
                "discord_id": payload.discord_id,
                "broski_to_spend": 300,
                "modules_completed": payload.course_modules_completed,
            },
        )
        if provision_resp.status_code != 200:
            raise HTTPException(status_code=provision_resp.status_code, detail=provision_resp.text)

        data = provision_resp.json()
        event = PetProvisionEvent(
            source_id=payload.source_id,
            discord_id=payload.discord_id,
            pet_id=data.get("pet_id"),
        )
        db.add(event)
        db.commit()
        return PetProvisionResponse.model_validate(data)
    except HTTPException:
        try:
            broski_service.award_coins(user_id=user.id, amount=300, reason="Refund: pet mint failed", db=db)
        except Exception:
            pass
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="source_id already processed — no double mint")


@router.post("/feed", response_model=PetFeedResponse)
async def feed_pet(
    payload: PetFeedRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_shop_secret),
) -> Any:
    user = db.query(models.User).filter(models.User.discord_id == payload.discord_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No V2.4 user linked to that Discord ID")

    try:
        status_resp = await _pets_bridge_get(f"/pet/{payload.discord_id}/status", timeout_s=3.0)
        if status_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="No pet found for this discord_id")
    except HTTPException:
        raise
    except Exception:
        pass

    try:
        broski_service.spend_coins(user_id=user.id, amount=10, reason="Feed BROskiPet", db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        resp = await _pets_bridge_post(f"/pet/{payload.discord_id}/feed", {})
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return PetFeedResponse.model_validate(resp.json())
    except HTTPException:
        try:
            broski_service.award_coins(user_id=user.id, amount=10, reason="Refund: pet feed failed", db=db)
        except Exception:
            pass
        raise


@router.get("/status/{discord_id}")
async def get_pet_status(discord_id: str) -> Any:
    resp = await _pets_bridge_get(f"/pet/{discord_id}/status", timeout_s=6.0)
    return resp.json()


@router.post("/chat/{discord_id}")
async def chat_with_pet(discord_id: str, body: dict[str, Any]) -> Any:
    resp = await _pets_bridge_post(f"/pet/{discord_id}/chat", body, timeout_s=30.0)
    return resp.json()


@router.get("/powers/{discord_id}")
async def get_pet_powers(discord_id: str) -> Any:
    resp = await _pets_bridge_get(f"/pet/{discord_id}/powers", timeout_s=6.0)
    return resp.json()


@router.get("/leaderboard")
async def get_pet_leaderboard(rarity: Optional[str] = None) -> Any:
    q = ""
    if rarity:
        q = f"?rarity={rarity}"
    resp = await _pets_bridge_get(f"/leaderboard{q}", timeout_s=8.0)
    return resp.json()
