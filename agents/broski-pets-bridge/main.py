import os
import json
import uuid
import asyncio
import subprocess
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


def _workspace_path() -> str:
    return os.getenv("WORKSPACE_PATH", "/workspace")


def _squad_json_path() -> str:
    return os.getenv("SQUAD_JSON_PATH", os.getenv("SQUAD_JSON_PATH", "/workspace/squad.json"))


def _read_text_file(path: str, limit_chars: int) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(limit_chars + 1)
    except Exception:
        return ""
    return data[:limit_chars]


def _recent_git_diff(limit_chars: int) -> str:
    workspace = _workspace_path()
    chunks: list[str] = []
    try:
        res = subprocess.run(
            ["git", "-C", workspace, "log", "-1", "--pretty=oneline"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        out = (res.stdout or "").strip()
        if out:
            chunks.append(f"Last commit: {out}")
    except Exception:
        pass

    for cmd in (
        ["git", "-C", workspace, "diff", "--no-color", "--stat", "HEAD~1..HEAD"],
        ["git", "-C", workspace, "diff", "--no-color", "--stat"],
    ):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            out = (res.stdout or "").strip()
            if out:
                chunks.append("Diff stat:\n" + out)
                break
        except Exception:
            continue

    combined = "\n".join(chunks).strip()
    return combined[:limit_chars] if combined else ""


def _load_squad() -> dict:
    path = _squad_json_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _mcp_base_url() -> str:
    raw = os.getenv("MCP_GATEWAY_URL", "http://mcp-gateway:8099").strip().rstrip("/")
    if raw.startswith("tcp://"):
        raw = "http://" + raw[len("tcp://") :]
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw
    return raw


def _mcp_headers() -> dict[str, str]:
    token = os.getenv("MCP_GATEWAY_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def _parse_mcp_sse_payload(text: str) -> dict:
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[len("data:") :].strip()
        if not raw:
            continue
        try:
            return json.loads(raw)
        except Exception:
            continue
    raise ValueError("Invalid MCP SSE response")


async def _mcp_jsonrpc_call(message: dict, timeout_s: float, session_id: str | None = None) -> tuple[dict, str | None]:
    base = _mcp_base_url()
    endpoints = [f"{base}/mcp", base]
    headers = {"Accept": "application/json, text/event-stream", **_mcp_headers()}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    async with httpx.AsyncClient(timeout=timeout_s, headers=headers) as client:
        last_err: Exception | None = None
        for url in endpoints:
            try:
                resp = await client.post(url, json=message)
                if resp.status_code == 200:
                    sid = resp.headers.get("Mcp-Session-Id") or session_id
                    return _parse_mcp_sse_payload(resp.text), sid
                last_err = HTTPException(status_code=resp.status_code, detail=resp.text)
            except Exception as e:
                last_err = e
                continue
        raise last_err or RuntimeError("MCP call failed")


async def _mcp_connected(timeout_s: float = 1.0) -> bool:
    try:
        _resp, _sid = await _mcp_jsonrpc_call(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "broski-pets-bridge", "version": "2.4"},
                },
            },
            timeout_s=timeout_s,
        )
        return True
    except Exception:
        return False


def _select_github_search_tool(tools: list[dict]) -> dict | None:
    preferred = [
        "github.search_issues",
        "github.search_pull_requests",
        "github.search_issues_and_prs",
        "github.search",
        "search_issues",
        "search_pull_requests",
        "search_issues_and_prs",
        "search",
    ]
    by_name: dict[str, dict] = {}
    for t in tools:
        name = t.get("name")
        if isinstance(name, str):
            by_name[name] = t

    for name in preferred:
        if name in by_name:
            return by_name[name]

    for name, tool in by_name.items():
        if "search" in name:
            return tool
    return None


def _build_tool_args(tool: dict, query: str) -> dict:
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") if isinstance(schema, dict) else {}
    if not isinstance(props, dict):
        props = {}

    args: dict[str, object] = {}
    repo = os.getenv("GITHUB_CONTEXT_REPO", "welshDog/HyperCode-V2.4")

    q_key = "query" if "query" in props else ("q" if "q" in props else None)
    if q_key:
        args[q_key] = f"repo:{repo} {query}"
    else:
        args["query"] = f"repo:{repo} {query}"

    if "repo" in props:
        args["repo"] = repo
    if "repository" in props:
        args["repository"] = repo
    if "owner" in props and "repo" in props:
        if "/" in repo:
            owner, name = repo.split("/", 1)
            args["owner"] = owner
            args["repo"] = name

    if "limit" in props:
        args["limit"] = 5
    if "per_page" in props:
        args["per_page"] = 5

    return args


async def _github_context_via_mcp(question: str) -> str:
    _resp, sid = await _mcp_jsonrpc_call(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "broski-pets-bridge", "version": "2.4"},
            },
        },
        timeout_s=10.0,
    )

    tools_resp, sid = await _mcp_jsonrpc_call(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        timeout_s=15.0,
        session_id=sid,
    )
    tools = tools_resp.get("result", {}).get("tools", [])
    if not isinstance(tools, list):
        return ""

    tool = _select_github_search_tool([t for t in tools if isinstance(t, dict)])
    if not tool:
        return ""

    tool_name = tool.get("name")
    if not isinstance(tool_name, str):
        return ""

    args = _build_tool_args(tool, question)
    call_resp, _sid = await _mcp_jsonrpc_call(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        },
        timeout_s=30.0,
        session_id=sid,
    )

    result = call_resp.get("result") or {}
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    out = "\n\n".join(chunks).strip()
    return out[:2000]



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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    mode: Literal["chat", "ask"] = Field(default="chat")


@app.post("/pet/{discord_id}/chat")
async def pet_chat(discord_id: str, body: ChatRequest) -> dict[str, object]:
    pet = _load_pet(discord_id)
    if not pet:
        raise HTTPException(status_code=404, detail="No pet found for this discord_id")

    ollama_url = os.getenv("OLLAMA_URL", "http://hypercode-ollama:11434").rstrip("/")
    preferred_model = os.getenv("PETS_OLLAMA_MODEL", "qwen2.5:7b")
    model = preferred_model
    limit = int(os.getenv("PETS_CONTEXT_MAX_CHARS", "1200"))

    whats_done = _read_text_file(os.path.join(_workspace_path(), "WHATS_DONE.md"), limit)
    git_diff = _recent_git_diff(limit)

    squad = _load_squad()
    species = str(pet.get("species", "Unknown"))
    power = ""
    caps: list[str] = []
    entry = squad.get(species)
    if isinstance(entry, dict):
        power = str(entry.get("power", ""))
        raw_caps = entry.get("capabilities")
        if isinstance(raw_caps, list):
            caps = [str(x) for x in raw_caps][:20]

    name = str(pet.get("name", "BROskiPet"))
    rarity = str(pet.get("rarity", "Unknown"))
    level = int(pet.get("level", 1))
    hunger = int(pet.get("hunger", 0))
    energy = int(pet.get("energy", 0))
    happiness = int(pet.get("happiness", 0))

    style = "You are a helpful AI companion."
    if body.mode == "chat":
        style = "You are a helpful AI companion. Stay in character, be warm and concise."
    if body.mode == "ask":
        style = "You are a senior pair-programmer. Be concrete, step-by-step, and focused on solving the coding question."

    github_context = ""
    if body.mode == "ask":
        try:
            github_context = await _github_context_via_mcp(body.message)
        except Exception:
            github_context = ""

    prompt = (
        f"{style}\n"
        f"Pet: {name} | Species: {species} | Rarity: {rarity} | Stage: {level}\n"
        f"Vitals: hunger={hunger}/100 energy={energy}/100 happiness={happiness}/100\n"
        f"Species power: {power}\n"
        f"Capabilities: {', '.join(caps) if caps else 'none'}\n\n"
        f"Recent git diff (may be empty):\n{git_diff}\n\n"
        f"WHATS_DONE.md (may be empty):\n{whats_done}\n\n"
        f"GitHub context via MCP (may be empty):\n{github_context}\n\n"
        f"User message:\n{body.message}\n"
    )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                tags = await client.get(f"{ollama_url}/api/tags")
                if tags.status_code == 200:
                    models = tags.json().get("models") or []
                    names = [m.get("name") for m in models if isinstance(m, dict)]
                    names = [n for n in names if isinstance(n, str)]
                    if names and preferred_model not in names:
                        model = names[0]
            except Exception:
                model = preferred_model

            res = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7 if body.mode == "chat" else 0.3,
                        "top_p": 0.9,
                        "num_predict": 128,
                    },
                },
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Ollama unavailable: {type(exc).__name__}: {exc}"
        )

    if res.status_code != 200:
        raise HTTPException(status_code=503, detail="Ollama request failed")

    payload = res.json()
    reply = str(payload.get("response", "")).strip()
    return {
        "reply": reply,
        "model": model,
        "pet": {"name": name, "species": species, "rarity": rarity, "level": level},
    }


class FeedRequest(BaseModel):
    spent_broski: int = Field(default=10, ge=0, le=10_000)


@app.post("/pet/{discord_id}/feed")
async def pet_feed(discord_id: str, body: FeedRequest | None = None) -> dict[str, object]:
    pet = _load_pet(discord_id)
    if not pet:
        raise HTTPException(status_code=404, detail="No pet found for this discord_id")

    spent = 10 if body is None else int(body.spent_broski)
    if spent != 10:
        raise HTTPException(status_code=422, detail="spent_broski must be 10")

    hunger = int(pet.get("hunger", 0))
    energy = int(pet.get("energy", 0))
    happiness = int(pet.get("happiness", 0))

    pet["hunger"] = min(100, hunger + 30)
    pet["energy"] = min(100, energy + 20)
    pet["happiness"] = min(100, happiness + 5)
    pet["last_fed_at"] = _now_iso()
    pet["updated_at"] = _now_iso()
    _save_pet(discord_id, pet)

    return {
        "fed": True,
        "spent_broski": spent,
        "hunger": int(pet["hunger"]),
        "energy": int(pet["energy"]),
        "happiness": int(pet["happiness"]),
    }


@app.get("/pet/{discord_id}/powers")
async def pet_powers(discord_id: str) -> dict[str, object]:
    pet = _load_pet(discord_id)
    if not pet:
        raise HTTPException(status_code=404, detail="No pet found for this discord_id")

    squad = _load_squad()
    species = str(pet.get("species", "Unknown"))
    entry = squad.get(species, {}) if isinstance(squad, dict) else {}
    power = ""
    caps: list[str] = []
    if isinstance(entry, dict):
        power = str(entry.get("power", ""))
        raw_caps = entry.get("capabilities")
        if isinstance(raw_caps, list):
            caps = [str(x) for x in raw_caps][:20]

    level = int(pet.get("level", 1))
    unlocked = ["status", "chat"]
    if level >= 2:
        unlocked.append("ask")
    if level >= 3:
        unlocked.append("powers")
    if level >= 4:
        unlocked.append("feed")
    if level >= 5:
        unlocked.append("special_power")
    if level >= 6:
        unlocked.append("quantum_mode")

    return {
        "species": species,
        "power": power,
        "capabilities": caps,
        "unlocked": unlocked,
        "stage": level,
    }


@app.get("/leaderboard")
async def leaderboard() -> list[dict[str, object]]:
    r = _redis()
    out: list[dict[str, object]] = []

    for key in r.scan_iter(match="pet:*"):
        if not isinstance(key, str):
            continue
        discord_id = key[len("pet:") :]
        raw = r.get(key)
        if not raw:
            continue
        try:
            pet = json.loads(raw)
        except Exception:
            continue
        if not isinstance(pet, dict):
            continue

        out.append(
            {
                "discord_id": discord_id,
                "name": str(pet.get("name", "Unknown")),
                "species": str(pet.get("species", "Unknown")),
                "level": int(pet.get("level", 1)),
                "xp": int(pet.get("xp", 0)),
            }
        )

    out.sort(key=lambda x: int(x.get("xp", 0)), reverse=True)
    top = out[:10]
    ranked: list[dict[str, object]] = []
    for i, row in enumerate(top, start=1):
        ranked.append(
            {
                "rank": i,
                "discord_id": row["discord_id"],
                "name": row["name"],
                "species": row["species"],
                "level": row["level"],
                "xp": row["xp"],
            }
        )
    return ranked


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

    mcp_ok = False
    try:
        mcp_ok = await _mcp_connected()
    except Exception:
        mcp_ok = False

    return {
        "status": "ok",
        "service": "broski-pets-bridge",
        "pets_enabled": pets_enabled,
        "ollama_connected": ollama_connected,
        "redis_connected": redis_connected,
        "mcp_connected": mcp_ok,
        "redis_db": 3,
    }
