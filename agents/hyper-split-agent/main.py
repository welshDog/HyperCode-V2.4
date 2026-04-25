from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="HyperSplit Agent", version="1.0.0")


class SplitRequest(BaseModel):
    task: str = Field(min_length=1, max_length=10_000)
    max_microtasks: int = Field(default=5, ge=3, le=7)


class Microtask(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=300)
    estimated_mins: int = Field(ge=5, le=60)
    priority: Literal["high", "medium", "low"]


class SplitResponse(BaseModel):
    original_task: str
    microtasks: list[Microtask]
    total_estimated_mins: int


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    candidate = text[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON was not an object")
    return parsed


def _normalize_microtasks(items: list[dict[str, Any]], max_microtasks: int) -> list[Microtask]:
    normalized: list[Microtask] = []
    for index, raw in enumerate(items[:max_microtasks], start=1):
        payload = dict(raw)
        payload["id"] = int(payload.get("id") or index)
        title = str(payload.get("title") or "").strip()
        payload["title"] = title
        mins = int(payload.get("estimated_mins") or payload.get("estimated_minutes") or 15)
        payload["estimated_mins"] = max(10, min(25, mins))
        prio = str(payload.get("priority") or "medium").strip().lower()
        payload["priority"] = prio if prio in {"high", "medium", "low"} else "medium"
        normalized.append(Microtask(**payload))
    return normalized


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "hyper-split"}


@app.post("/split", response_model=SplitResponse)
async def split_task(req: SplitRequest) -> SplitResponse:
    ollama_host = _env("OLLAMA_HOST", "http://hypercode-ollama:11434").rstrip("/")
    model = _env("OLLAMA_MODEL", "qwen2.5-coder:3b")
    timeout = httpx.Timeout(30.0, connect=5.0)
    transport = httpx.AsyncHTTPTransport(retries=2)

    prompt = (
        "You are HyperSplit, an ADHD-friendly task decomposer.\n"
        f"Break the task into {req.max_microtasks} microtasks.\n"
        "Each microtask must be completable in 10-25 minutes.\n"
        "Return ONLY valid JSON with this exact shape:\n"
        '{"microtasks":[{"id":1,"title":"...","estimated_mins":15,"priority":"high"}]}\n'
        f"Task: {req.task}\n"
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            resp = await client.post(
                f"{ollama_host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Ollama error ({status}): {detail}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    raw = body.get("response")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=502, detail="Ollama response missing 'response' text")

    try:
        parsed = _extract_json_object(raw)
        microtasks_raw = parsed.get("microtasks")
        if not isinstance(microtasks_raw, list):
            raise ValueError("Missing 'microtasks' list in model output JSON")
        microtasks = _normalize_microtasks(microtasks_raw, req.max_microtasks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to parse microtasks JSON: {exc}")

    return SplitResponse(
        original_task=req.task,
        microtasks=microtasks,
        total_estimated_mins=sum(m.estimated_mins for m in microtasks),
    )
