import os
import json
import uuid
from datetime import datetime, timezone
from secrets import SystemRandom
from typing import Literal

import httpx
import redis
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


app = FastAPI(title="broski-pets-bridge")
_rand = SystemRandom()

Rarity = Literal["Common", "Uncommon", "Rare", "Legendary"]

EVOLUTION_THRESHOLDS: list[tuple[int, int]] = [
    (0, 1),
    (500, 2),
    (2000, 3),
    (5000, 4),
    (15000, 5),
    (50000, 6),
]

SPECIES_BY_RARITY: dict[Rarity, list[str]] = {
    "Common": ["CatEep", "DogEep", "RabbitEep", "FishEep", "BirdEep"],
    "Uncommon": ["FoxEep", "WolfEep", "BearEep", "TigerEep"],
    "Rare": ["SharkEep", "OwlEep", "DragonEep"],
    "Legendary": ["SpiderEep", "VenomEep", "PhoenixEep"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redis() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/3")
    return redis.from_url(redis_url, socket_timeout=2, decode_responses=True)


def _get_env_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise HTTPException(status_code=503, detail=f"{name} not configured")
    return val


def _verify_secret(expected_env: str, header_value: str | None, header_name: str) -> None:
    expected = _get_env_required(expected_env)
    if not header_value:
        raise HTTPException(status_code=401, detail=f"{header_name} header required")
    if header_value != expected:
        raise HTTPException(status_code=401, detail="Invalid secret")



def _pet_key(discord_id: str) -> str:
    return f"pet:{discord_id}"


def _load_pet(discord_id: str) -> dict | None:
    raw = _redis().get(_pet_key(discord_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _save_pet(discord_id: str, pet: dict) -> None:
    _redis().set(_pet_key(discord_id), json.dumps(pet, separators=(",", ":")))


def _streak_key(discord_id: str) -> str:
    return f"petstreak:{discord_id}"


def _xp_to_stage(xp: int) -> int:
    stage = 1
    for threshold, lvl in EVOLUTION_THRESHOLDS:
        if xp >= threshold:
            stage = lvl
    return stage


def _next_threshold_xp(xp: int) -> int | None:
    for threshold, _lvl in EVOLUTION_THRESHOLDS:
        if xp < threshold:
            return threshold
    return None


def _roll_rarity(modules_completed: int) -> Rarity:
    if modules_completed <= 1:
        weights: list[tuple[Rarity, int]] = [
            ("Common", 80),
            ("Uncommon", 18),
            ("Rare", 2),
        ]
    elif 2 <= modules_completed <= 4:
        weights = [
            ("Common", 50),
            ("Uncommon", 35),
            ("Rare", 13),
            ("Legendary", 2),
        ]
    else:
        weights = [
            ("Common", 20),
            ("Uncommon", 30),
            ("Rare", 35),
            ("Legendary", 15),
        ]

    roll = _rand.randrange(1, sum(w for _r, w in weights) + 1)
    upto = 0
    for rarity, w in weights:
        upto += w
        if roll <= upto:
            return rarity
    return "Common"


def _generate_pet_name(species: str) -> str:
    adjectives = [
        "Brave",
        "Cosmic",
        "Snappy",
        "Quiet",
        "Hyper",
        "Nimble",
        "Spark",
        "Glitch",
        "Sunny",
        "Shadow",
    ]
    base = species.replace("Eep", "")
    return f"{_rand.choice(adjectives)} {base}"


class ProvisionRequest(BaseModel):
    discord_id: str = Field(..., min_length=1, max_length=64)
    broski_to_spend: int = Field(default=300, ge=1, le=10_000)
    modules_completed: int = Field(default=0, ge=0, le=10_000)


class ProvisionResponse(BaseModel):
    pet_id: str
    name: str
    species: str
    rarity: Rarity
    message: str


class XpAwardRequest(BaseModel):
    discord_id: str = Field(..., min_length=1, max_length=64)
    amount: int = Field(..., ge=1, le=1_000_000)
    reason: str = Field(..., min_length=1, max_length=200)
    source: str = Field(default="unknown", min_length=1, max_length=64)


class XpAwardResponse(BaseModel):
    new_xp: int
    new_level: int
    evolved: bool
    evolution_message: str | None


def _award_xp_to_pet(discord_id: str, amount: int, reason: str, source: str) -> XpAwardResponse:
    pet = _load_pet(discord_id)
    if not pet:
        raise HTTPException(status_code=404, detail="No pet found for this discord_id")

    old_xp = int(pet.get("xp", 0))
    old_level = int(pet.get("level", 1))

    new_xp = old_xp + amount
    new_level = _xp_to_stage(new_xp)

    evolved = new_level > old_level
    evolution_message = None
    if evolved:
        evolution_message = f"{pet.get('name', 'Your pet')} evolved to Stage {new_level}!"

    pet["xp"] = new_xp
    pet["level"] = new_level
    pet["updated_at"] = _now_iso()

    history = pet.get("evolution_history")
    if not isinstance(history, list):
        history = []
    if evolved:
        history.append(
            {
                "from_level": old_level,
                "to_level": new_level,
                "at": pet["updated_at"],
                "reason": reason,
                "source": source,
                "xp": new_xp,
            }
        )
    pet["evolution_history"] = history

    _save_pet(discord_id, pet)

    return XpAwardResponse(
        new_xp=new_xp,
        new_level=new_level,
        evolved=evolved,
        evolution_message=evolution_message,
    )


@app.post("/provision", response_model=ProvisionResponse)
async def provision(body: ProvisionRequest) -> ProvisionResponse:
    if body.broski_to_spend != 300:
        raise HTTPException(status_code=422, detail="broski_to_spend must be 300 for Phase 1")

    existing = _load_pet(body.discord_id)
    if existing:
        raise HTTPException(status_code=409, detail="Pet already exists for this discord_id")

    rarity = _roll_rarity(body.modules_completed)
    species = _rand.choice(SPECIES_BY_RARITY[rarity])
    pet_id = str(uuid.uuid4())
    name = _generate_pet_name(species)
    now = _now_iso()

    pet = {
        "pet_id": pet_id,
        "name": name,
        "species": species,
        "rarity": rarity,
        "level": 1,
        "xp": 0,
        "hunger": 50,
        "energy": 80,
        "happiness": 70,
        "modules_completed_at_mint": body.modules_completed,
        "created_at": now,
        "updated_at": now,
        "evolution_history": [],
    }
    _save_pet(body.discord_id, pet)

    return ProvisionResponse(
        pet_id=pet_id,
        name=name,
        species=species,
        rarity=rarity,
        message=f"Your {name} has hatched! 🐾",
    )


@app.post("/xp/award", response_model=XpAwardResponse)
async def award_xp(body: XpAwardRequest) -> XpAwardResponse:
    return _award_xp_to_pet(body.discord_id, body.amount, body.reason, body.source)


@app.get("/pet/{discord_id}/status")
async def pet_status(discord_id: str) -> dict[str, object]:
    pet = _load_pet(discord_id)
    if not pet:
        raise HTTPException(status_code=404, detail="No pet found for this discord_id")

    xp = int(pet.get("xp", 0))
    nxt = _next_threshold_xp(xp)
    pet_out = dict(pet)
    pet_out["next_evolution_xp"] = None if nxt is None else max(0, nxt - xp)
    return pet_out


class StreakCommitRequest(BaseModel):
    discord_id: str = Field(..., min_length=1, max_length=64)
    commit_sha: str = Field(..., min_length=1, max_length=64)
    commit_message: str = Field(default="", max_length=500)
    committed_at: str | None = None


@app.post("/streak/commit")
async def streak_commit(body: StreakCommitRequest) -> dict[str, object]:
    try:
        when = datetime.fromisoformat(body.committed_at) if body.committed_at else datetime.now(timezone.utc)
    except Exception:
        when = datetime.now(timezone.utc)

    day = when.astimezone(timezone.utc).date().isoformat()
    r = _redis()
    key = _streak_key(body.discord_id)
    raw = r.get(key)
    state: dict[str, object] = {}
    if raw:
        try:
            state = json.loads(raw)
        except Exception:
            state = {}

    last_day = str(state.get("last_day", ""))
    streak_days = int(state.get("streak_days", 0) or 0)
    rewarded_at_7 = bool(state.get("rewarded_at_7", False))

    if last_day == day:
        pass
    else:
        try:
            last_dt = datetime.fromisoformat(last_day).date()
            cur_dt = datetime.fromisoformat(day).date()
            delta = (cur_dt - last_dt).days
        except Exception:
            delta = 999

        if delta == 1:
            streak_days = max(1, streak_days + 1)
        else:
            streak_days = 1
            rewarded_at_7 = False

    state = {"last_day": day, "streak_days": streak_days, "rewarded_at_7": rewarded_at_7}
    r.set(key, json.dumps(state, separators=(",", ":")))

    award_bonus = False
    if streak_days >= 7 and rewarded_at_7 is False:
        award_bonus = True
        state["rewarded_at_7"] = True
        r.set(key, json.dumps(state, separators=(",", ":")))

    return {"streak_days": streak_days, "award_bonus": award_bonus}


class WebhookAwardRequest(BaseModel):
    source_id: str = Field(..., min_length=1, max_length=128)
    discord_id: str = Field(..., min_length=1, max_length=64)
    module_slug: str | None = Field(default=None, max_length=128)
    critical_count: int | None = Field(default=None, ge=0, le=10_000)


@app.post("/webhooks/pytest-pass")
async def webhook_pytest_pass(
    body: WebhookAwardRequest,
    x_pets_secret: str | None = Header(default=None, alias="X-Pets-Secret"),
) -> dict[str, object]:
    _verify_secret("PETS_WEBHOOK_SECRET", x_pets_secret, "X-Pets-Secret")
    key = f"petwebhook:pytest:{body.source_id}"
    r = _redis()
    if not r.set(key, "1", nx=True, ex=60 * 60 * 24 * 14):
        return {"awarded": False, "duplicate": True}
    res = _award_xp_to_pet(body.discord_id, 50, "Pytest all green", "pytest_webhook")
    return {"awarded": True, "result": res.model_dump()}


@app.post("/webhooks/trivy-clean")
async def webhook_trivy_clean(
    body: WebhookAwardRequest,
    x_pets_secret: str | None = Header(default=None, alias="X-Pets-Secret"),
) -> dict[str, object]:
    _verify_secret("PETS_WEBHOOK_SECRET", x_pets_secret, "X-Pets-Secret")
    if body.critical_count is None:
        raise HTTPException(status_code=422, detail="critical_count is required")
    key = f"petwebhook:trivy:{body.source_id}"
    r = _redis()
    if not r.set(key, "1", nx=True, ex=60 * 60 * 24 * 14):
        return {"awarded": False, "duplicate": True}
    if body.critical_count != 0:
        return {"awarded": False, "critical_count": body.critical_count}
    res = _award_xp_to_pet(body.discord_id, 100, "Trivy 0 CRITICAL", "trivy_webhook")
    return {"awarded": True, "result": res.model_dump()}


@app.post("/webhooks/course-module-complete")
async def webhook_course_module_complete(
    body: WebhookAwardRequest,
    x_sync_secret: str | None = Header(default=None, alias="X-Sync-Secret"),
) -> dict[str, object]:
    _verify_secret("COURSE_SYNC_SECRET", x_sync_secret, "X-Sync-Secret")
    key = f"petwebhook:course:{body.source_id}"
    r = _redis()
    if not r.set(key, "1", nx=True, ex=60 * 60 * 24 * 60):
        return {"awarded": False, "duplicate": True}
    slug = body.module_slug or "module_complete"
    res = _award_xp_to_pet(body.discord_id, 150, f"Course module complete: {slug}", "course_webhook")
    return {"awarded": True, "result": res.model_dump()}


@app.get("/health")
async def health() -> dict[str, object]:
    ollama_url = os.getenv("OLLAMA_URL", "http://hypercode-ollama:11434").rstrip("/")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/3")
    pets_enabled = _is_true(os.getenv("PETS_ENABLED"))

    ollama_connected = False
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            ollama_connected = resp.status_code == 200
    except Exception:
        ollama_connected = False

    redis_connected = False
    try:
        r = redis.from_url(redis_url, socket_timeout=2, decode_responses=True)
        redis_connected = r.ping() is True
    except Exception:
        redis_connected = False

    return {
        "status": "ok",
        "service": "broski-pets-bridge",
        "pets_enabled": pets_enabled,
        "ollama_connected": ollama_connected,
        "redis_connected": redis_connected,
        "redis_db": 3,
    }
