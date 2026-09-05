"""OpenRouter model routing: which specialized route (if any) a request
should use, secret redaction for privacy-mode routes, and the actual
circuit-breaker-wrapped HTTP call.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal, Optional

import httpx
from app.core.circuit_breaker import get_breaker

_llm_breaker = get_breaker("llm-router", fail_max=3, reset_timeout=30)


PrivacyMode = Literal["redact", "none"]
RouteName = Literal["hunter_alpha", "healer_alpha"]


@dataclass(frozen=True)
class ModelRouteContext:
    """Signals `select_model_route()` uses to decide whether a specialized route applies."""

    kind: str
    context_tokens_estimate: int = 0
    cross_repo: bool = False
    has_images: bool = False
    has_audio: bool = False
    requires_signal_correlation: bool = False


@dataclass(frozen=True)
class ModelRoute:
    """A resolved specialized route: which model/endpoint/privacy mode to use."""

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
    """Replace recognizable API-key/token patterns with `[REDACTED]`."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _apply_privacy_mode(value: str, mode: PrivacyMode) -> str:
    """Redact secrets in `value` if `mode == "redact"`; pass through otherwise."""
    if mode == "redact":
        return redact_secrets(value)
    return value


def select_model_route(ctx: ModelRouteContext, settings: Any) -> Optional[ModelRoute]:
    """Pick a specialized route (healer_alpha, then hunter_alpha) if `ctx`
    matches one and its feature flag is enabled; None falls back to the
    caller's default routing.
    """
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
    """Call OpenRouter's chat/completions through the circuit breaker.

    Applies `privacy_mode` to message content before sending. Raises
    `RuntimeError` on a non-200 response or an unexpected/empty response
    shape (no choices, no message content) rather than letting a raw
    `KeyError`/`IndexError` escape.
    """
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

    async def _do_call() -> str:
        """The actual request, wrapped by the circuit breaker in the caller."""
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers
            )
            if resp.status_code != 200:
                body_preview = (resp.text or "")[:500]
                raise RuntimeError(f"OpenRouter error {resp.status_code}: {body_preview}")
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError(f"OpenRouter returned no choices: {str(data)[:500]}")
            content = (choices[0].get("message") or {}).get("content")
            if not isinstance(content, str):
                raise RuntimeError("OpenRouter returned no message content")
            return content

    return await _llm_breaker.call(_do_call)
