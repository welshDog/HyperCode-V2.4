from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal, Optional

import httpx


PrivacyMode = Literal["redact", "none"]
RouteName = Literal["hunter_alpha", "healer_alpha"]


@dataclass(frozen=True)
class ModelRouteContext:
    kind: str
    context_tokens_estimate: int = 0
    cross_repo: bool = False
    has_images: bool = False
    has_audio: bool = False
    requires_signal_correlation: bool = False


@dataclass(frozen=True)
class ModelRoute:
    name: RouteName
    provider: Literal["openrouter"]
    base_url: str
    model: str
    max_tokens: int
    route_tag: str
    privacy_mode: PrivacyMode


_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _apply_privacy_mode(value: str, mode: PrivacyMode) -> str:
    if mode == "redact":
        return redact_secrets(value)
    return value


def select_model_route(ctx: ModelRouteContext, settings: Any) -> Optional[ModelRoute]:
    if (
        settings.HEALER_ALPHA_ENABLED
        and (
            ctx.has_images
            or ctx.has_audio
            or ctx.requires_signal_correlation
            or ctx.kind.lower() in {"incident", "recovery", "triage", "self_heal", "health"}
        )
    ):
        return ModelRoute(
            name="healer_alpha",
            provider="openrouter",
            base_url=settings.HEALER_ALPHA_BASE_URL,
            model=settings.HEALER_ALPHA_MODEL,
            max_tokens=settings.HEALER_ALPHA_MAX_TOKENS,
            route_tag=settings.HEALER_ALPHA_ROUTE_TAG,
            privacy_mode=settings.HEALER_ALPHA_PRIVACY_MODE,
        )

    if settings.HUNTER_ALPHA_ENABLED and (
        ctx.cross_repo
        or ctx.context_tokens_estimate > 120_000
        or ctx.kind.lower() in {"architecture", "roadmap", "system_design", "evolution", "planning"}
    ):
        return ModelRoute(
            name="hunter_alpha",
            provider="openrouter",
            base_url=settings.HUNTER_ALPHA_BASE_URL,
            model=settings.HUNTER_ALPHA_MODEL,
            max_tokens=settings.HUNTER_ALPHA_MAX_TOKENS,
            route_tag=settings.HUNTER_ALPHA_ROUTE_TAG,
            privacy_mode=settings.HUNTER_ALPHA_PRIVACY_MODE,
        )

    return None


async def openrouter_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    privacy_mode: PrivacyMode,
    timeout_seconds: float = 60.0,
) -> str:
    safe_messages: list[dict[str, str]] = []
    for msg in messages:
        safe_messages.append(
            {
                "role": msg.get("role", "user"),
                "content": _apply_privacy_mode(msg.get("content", ""), privacy_mode),
            }
        )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "model": model,
        "messages": safe_messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
        if resp.status_code != 200:
            body_preview = (resp.text or "")[:500]
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {body_preview}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]
