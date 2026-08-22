"""broski-coo -- read-only COO/observer agent for the HyperCode-V2.4 fleet.

v1 scope: HyperCode-V2.4 only, strictly read-only. No Docker socket, no
DOCKER_HOST, no calls to agent-registry's mutation routes
(POST /agents/{name}/restart, POST /agents/{name}/reset) -- this file must
never call them. Fully stateless: no Redis, no DB, one HTTP call out
(agent-registry) + three local file reads + one LLM call per /brief request.

Every fact in a /brief response must trace back to data fetched in that same
request -- this agent exists specifically to not repeat the mistake of two
AI-generated messages pasted into the design session that contained
plausible-sounding but fabricated specifics (a "free models" table where
7/8 entries were wrong; a claimed "~30 containers" and a nonexistent
NEXT_SESSION_HANDOVER_LATEST.md file). See HYPER-AGENT-BIBLE.md.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

logger = logging.getLogger("broski-coo")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [broski-coo] %(message)s")

app = FastAPI(title="BROski COO", version="1.0.0")


# --- auth middleware -- mirrors agents/super-hyper-broski-agent/main.py verbatim ---
@app.middleware("http")
async def _agent_auth_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/" or path.startswith("/health") or path.startswith("/metrics"):
        return await call_next(request)

    expected = (os.getenv("HYPERCODE_API_KEY") or os.getenv("AGENT_API_KEY") or "").strip()
    if not expected:
        return Response(status_code=503, content="Agent API key not configured", media_type="text/plain")

    provided = request.headers.get("x-agent-key") or request.headers.get("x-api-key")
    if not provided or not secrets.compare_digest(str(provided), expected):
        return Response(status_code=401, content="Invalid or missing API key", media_type="text/plain")

    return await call_next(request)


# --- config ---
AGENT_REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8077").rstrip("/")
REPO_ROOT_PATH = os.getenv("REPO_ROOT_PATH", "/app/repo")


# --- LLM fallback chain: Anthropic -> OpenRouter(free) -> Ollama ---
# _OllamaAdapter mirrors agents/base-agent/agent.py's version exactly (that
# file is not imported -- agents in this fleet duplicate this shape by
# established convention rather than sharing a module).
class _OllamaAdapter:
    """Thin Anthropic-interface wrapper over the Ollama OpenAI-compat endpoint."""

    def __init__(self, model: str, base_url: str, api_key: str):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self.messages = self  # so client.messages.create() works

    async def create(self, model=None, max_tokens=1000, messages=None, system=None, **kwargs):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages or [])

        class _Msg:
            def __init__(self, text):
                self.text = text

        class _Resp:
            def __init__(self, text):
                self.content = [_Msg(text)]

        resp = await self._client.chat.completions.create(
            model=model or self._model,
            max_tokens=max_tokens,
            messages=msgs,
        )
        return _Resp(resp.choices[0].message.content or "")


# OpenRouter free-tier adapter -- request shape ported (not imported; backend/
# is never importable from agents/) from backend/app/core/model_routes.py's
# openrouter_chat(). The circuit breaker there (backend/app/core/circuit_
# breaker.py) is deliberately not ported -- not importable from agents/, and
# the free-model rotation below already provides equivalent failure-cycling.
# redact_secrets/privacy_mode is also deliberately not ported -- this agent's
# payload is fleet status + this repo's own docs, not third-party/user
# content, so redaction isn't load-bearing here.
_free_model_cache: dict[str, Any] = {"models": [], "fetched_at": 0.0}
FREE_MODEL_CACHE_TTL_SECONDS = 300  # respects OpenRouter free-tier's shared 20 req/min cap

# Providers confirmed (via OpenRouter's own models page, reviewed by Lyndz
# during OpenRouter setup) to train on free-tier inputs/outputs. Excluded by
# provider-id prefix so this holds even as specific model slugs rotate.
# NOTE: an OpenRouter dashboard preset with an equivalent data_collection:
# deny rule was tried instead of this client-side filter first -- reverted
# (see docs/gotchas or WHATS_DONE.md) after live testing proved the preset
# mechanism doesn't reliably enforce its own policy: an explicit `model`
# field silently overrides both the preset's model selection AND its cost/
# training-data safety net. This denylist is a hard, code-level check that
# can't be silently bypassed by a request-time field.
_DENIED_PROVIDERS = {"poolside", "liquid"}


async def _discover_free_openrouter_models(client: httpx.AsyncClient) -> list[str]:
    now = time.time()
    if _free_model_cache["models"] and (now - _free_model_cache["fetched_at"]) < FREE_MODEL_CACHE_TTL_SECONDS:
        return _free_model_cache["models"]
    resp = await client.get("https://openrouter.ai/api/v1/models", timeout=10.0)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    free = [
        m["id"]
        for m in data
        if m.get("pricing", {}).get("prompt") == "0" and m["id"].split("/")[0] not in _DENIED_PROVIDERS
    ]
    _free_model_cache["models"] = free
    _free_model_cache["fetched_at"] = now
    return free


async def _openrouter_chat_free(system: str, user: str, max_tokens: int) -> tuple[str, str]:
    """Returns (text, model_used). Rotates across discovered free models on a
    non-2xx response. If all fail, raises -- caller falls through to Ollama."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    async with httpx.AsyncClient() as client:
        models = await _discover_free_openrouter_models(client)
        if not models:
            raise RuntimeError("no free OpenRouter models discovered")

        last_err: Optional[Exception] = None
        for model in models:
            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                }
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # Reasoning-capable free models (confirmed live: stealth/ox-alpha)
                    # can return content: null with finish_reason "length" -- the
                    # token budget was spent on internal reasoning before any
                    # output text was emitted. A 200 does not guarantee usable
                    # content; treat null/empty the same as a failed attempt and
                    # rotate to the next free model rather than propagating None
                    # up into a response typed as `brief: str`.
                    if not content:
                        last_err = RuntimeError(
                            f"OpenRouter {model} returned empty/null content "
                            "(likely spent max_tokens on reasoning before emitting output)"
                        )
                        continue
                    return content, model
                last_err = RuntimeError(f"OpenRouter {model} -> {resp.status_code}: {resp.text[:300]}")
            except Exception as e:  # noqa: BLE001 -- broad by design, matches repo's degrade convention
                last_err = e

        raise last_err or RuntimeError("all discovered free OpenRouter models failed")


async def _call_llm(system: str, user: str, max_tokens: int = 900) -> tuple[str, str]:
    """Anthropic -> OpenRouter(free) -> Ollama. Never raises past this point --
    matches this codebase's repo-wide 'catch broadly, log, return
    human-readable string' degrade style. Returns (brief_text, provider_label)."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            resp = await client.messages.create(
                model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text, "anthropic"
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Anthropic call failed, falling back: {e}")

    try:
        text, model = await _openrouter_chat_free(system, user, max_tokens)
        return text, f"openrouter:{model}"
    except Exception as e:  # noqa: BLE001
        logger.warning(f"OpenRouter free-tier call failed, falling back to Ollama: {e}")

    try:
        adapter = _OllamaAdapter(
            model=os.getenv("LLM_MODEL", "llama3.2"),
            base_url=os.getenv("LLM_API_BASE", "http://ollama:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "NA"),
        )
        resp = await adapter.create(
            max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}]
        )
        return resp.content[0].text, "ollama"
    except Exception as e:  # noqa: BLE001
        logger.error(f"All LLM providers failed: {e}")
        return "LLM call failed -- all providers (Anthropic, OpenRouter, Ollama) unreachable.", "none"


# --- source fetchers ---
async def _fetch_fleet_status() -> dict[str, Any]:
    """status: 'ok' | 'degraded' | 'unavailable'.

    'degraded' means agent-registry answered 200 but the payload looks
    empty/stale (e.g. summary.total == 0, or every agent status == 'unknown'
    because agent-registry's own Redis is down -- its _agent_status() falls
    back to 'unknown' per-field on an empty Redis hash rather than erroring,
    so a 200 does not by itself guarantee real data). Treating any 200 as
    good data would reproduce the exact hallucination class this agent
    exists to prevent.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{AGENT_REGISTRY_URL}/agents/status")
            resp.raise_for_status()
            data = resp.json()
        summary = data.get("summary", {})
        agents = data.get("agents", [])
        unknown_count = sum(1 for a in agents if a.get("status") == "unknown")
        degraded = summary.get("total", 0) == 0 or (bool(agents) and unknown_count == len(agents))
        return {"status": "degraded" if degraded else "ok", "summary": summary, "agents": agents}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"agent-registry unreachable: {e}")
        return {"status": "unavailable", "summary": {}, "agents": [], "error": str(e)}


_HANDOVER_RE = re.compile(r"NEXT_SESSION_HANDOVER_(\d{4}-\d{2}-\d{2})")


def _read_whats_done() -> dict[str, Any]:
    """Most recent dated entry only -- up to the first '---' divider after
    the header -- to control prompt size, not the whole file."""
    path = os.path.join(REPO_ROOT_PATH, "WHATS_DONE.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        parts = text.split("\n---\n", 2)
        excerpt = "\n---\n".join(parts[:2]) if len(parts) > 1 else text[:4000]
        return {"status": "ok", "path": "WHATS_DONE.md", "excerpt": excerpt[:6000]}
    except Exception as e:  # noqa: BLE001
        return {"status": "unavailable", "path": "WHATS_DONE.md", "error": str(e)}


def _read_next_tasks() -> dict[str, Any]:
    path = os.path.join(REPO_ROOT_PATH, "docs", "NEXT_TASKS.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        return {"status": "ok", "path": "docs/NEXT_TASKS.md", "excerpt": text[:6000]}
    except Exception as e:  # noqa: BLE001
        return {"status": "unavailable", "path": "docs/NEXT_TASKS.md", "error": str(e)}


def _newest_handover() -> dict[str, Any]:
    """Glob exactly two locations (repo root + docs/) -- NOT a recursive **/
    glob, which would also match vault/Ops-Logs/handovers/. Parse the
    leading YYYY-MM-DD and sort by (date, filename) for deterministic
    tie-breaking on same-date-different-suffix files (-evening /
    -late-night / bare)."""
    candidates: list[tuple[str, str, str]] = []
    for pattern in (
        os.path.join(REPO_ROOT_PATH, "NEXT_SESSION_HANDOVER_*.md"),
        os.path.join(REPO_ROOT_PATH, "docs", "NEXT_SESSION_HANDOVER_*.md"),
    ):
        for fp in glob.glob(pattern):
            m = _HANDOVER_RE.search(os.path.basename(fp))
            if m:
                candidates.append((m.group(1), os.path.basename(fp), fp))

    if not candidates:
        return {"status": "unavailable", "path": None, "error": "no handover files found"}

    candidates.sort()
    _, fname, fpath = candidates[-1]
    try:
        with open(fpath, encoding="utf-8") as fh:
            text = fh.read()
        return {"status": "ok", "path": fname, "excerpt": text[:6000]}
    except Exception as e:  # noqa: BLE001
        return {"status": "unavailable", "path": fname, "error": str(e)}


# --- prompt assembly ---
_SYSTEM_PROMPT = """You are BROski COO, a read-only observer for the HyperCode-V2.4 agent fleet.
You will be given real, freshly-fetched data: live fleet status counts, and
excerpts from WHATS_DONE.md, docs/NEXT_TASKS.md, and the newest dated
NEXT_SESSION_HANDOVER file. Some sources may be marked unavailable or
degraded -- say so plainly if they are, do not fill gaps with guesses.

Rules, no exceptions:
- Only state facts that are literally present in the data you were given below.
- Never invent a number, container name, file name, or status you were not given.
- If a source is unavailable or degraded, say exactly that -- do not describe
  its contents as if it were fetched successfully.
- Do not round or approximate counts ("about 30", "dozens of") -- use the
  exact numbers given, or state that no number was available.
- Keep the brief to plain English, a few short paragraphs. This is a status
  brief for a human, not a task list rewrite."""


def _build_user_prompt(fleet: dict, whats_done: dict, next_tasks: dict, handover: dict) -> str:
    return (
        "FLEET STATUS (agent-registry, source status=%s):\n%s\n\n"
        "WHATS_DONE.md (source status=%s, path=%s):\n%s\n\n"
        "docs/NEXT_TASKS.md (source status=%s, path=%s):\n%s\n\n"
        "Newest handover (source status=%s, path=%s):\n%s\n"
    ) % (
        fleet["status"],
        json.dumps(fleet.get("summary", {})),
        whats_done["status"],
        whats_done.get("path"),
        whats_done.get("excerpt", whats_done.get("error", "")),
        next_tasks["status"],
        next_tasks.get("path"),
        next_tasks.get("excerpt", next_tasks.get("error", "")),
        handover["status"],
        handover.get("path"),
        handover.get("excerpt", handover.get("error", "")),
    )


# --- models ---
class BriefResponse(BaseModel):
    brief: str
    provider_used: str
    generated_at: str
    sources: dict[str, Any]  # raw status + path + (for fleet) summary counts per source


# --- routes ---
@app.get("/")
async def root() -> dict[str, Any]:
    return {"agent": "broski-coo", "version": "1.0.0", "scope": "HyperCode-V2.4, read-only"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "broski-coo"}


@app.post("/brief", response_model=BriefResponse)
async def brief() -> BriefResponse:
    fleet = await _fetch_fleet_status()
    whats_done = _read_whats_done()
    next_tasks = _read_next_tasks()
    handover = _newest_handover()

    system = _SYSTEM_PROMPT
    user = _build_user_prompt(fleet, whats_done, next_tasks, handover)
    text, provider = await _call_llm(system, user)

    return BriefResponse(
        brief=text,
        provider_used=provider,
        generated_at=datetime.now(timezone.utc).isoformat(),
        sources={
            "fleet_status": {"status": fleet["status"], "summary": fleet.get("summary", {})},
            "whats_done": {"status": whats_done["status"], "path": whats_done.get("path")},
            "next_tasks": {"status": next_tasks["status"], "path": next_tasks.get("path")},
            "handover": {"status": handover["status"], "path": handover.get("path")},
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8025)))
