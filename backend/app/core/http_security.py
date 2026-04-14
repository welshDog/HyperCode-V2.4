from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

_RATE_LIMIT_SALT = (os.getenv("HYPERCODE_RATE_LIMIT_SALT") or "").strip()
if not _RATE_LIMIT_SALT:
    # Ephemeral salt is still better than storing raw IPs; set env var for stable behaviour across restarts.
    _RATE_LIMIT_SALT = os.urandom(16).hex()


def _anonymize_ip(ip: str) -> str:
    """Return a non-reversible identifier for rate-limit bucketing (privacy-first)."""
    h = hashlib.sha256()
    h.update(_RATE_LIMIT_SALT.encode("utf-8"))
    h.update(b":")
    h.update((ip or "unknown").encode("utf-8"))
    return h.hexdigest()[:16]


_PATH_ID_RE = re.compile(r"/\d+")


def _normalize_path(path: str) -> str:
    """
    Reduce accidental collection of user-identifying URL segments (privacy-first).
    Example: /api/v1/users/123 -> /api/v1/users/:id
    """
    return _PATH_ID_RE.sub("/:id", path or "/")


def _is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto")
    return forwarded_proto == "https"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enable_hsts: bool = True):
        super().__init__(app)
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.headers.setdefault("X-XSS-Protection", "0")

        if self._enable_hsts and _is_https(request):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        path = request.url.path
        if "/docs" not in path and "/redoc" not in path:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )

        return response


@dataclass(frozen=True)
class RateLimitConfig:
    enabled: bool
    window_seconds: int
    max_requests: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        config: RateLimitConfig,
        exempt_paths: Tuple[str, ...] = (),
    ):
        super().__init__(app)
        self._config = config
        self._exempt_paths = exempt_paths
        self._events: Dict[Tuple[str, str], Deque[float]] = {}
        self._lock = asyncio.Lock()

    def _evict_stale_keys(self, window_start: float) -> None:
        stale = [k for k, dq in self._events.items() if not dq or dq[-1] < window_start]
        for k in stale:
            del self._events[k]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._config.enabled:
            return await call_next(request)

        # Phase 10D — internal agents present X-Agent-Key and are governed by
        # per-agent Redis rate limits instead of the global IP-based limit.
        if request.headers.get("x-agent-key"):
            return await call_next(request)

        path = _normalize_path(request.url.path)
        for prefix in self._exempt_paths:
            if path.startswith(prefix):
                return await call_next(request)

        ip = _get_client_ip(request)
        anon = _anonymize_ip(ip)
        key = (anon, path)
        now = time.monotonic()
        window_start = now - self._config.window_seconds

        async with self._lock:
            self._evict_stale_keys(window_start)

            dq = self._events.get(key)
            if dq is None:
                dq = deque()
                self._events[key] = dq

            while dq and dq[0] < window_start:
                dq.popleft()

            if len(dq) >= self._config.max_requests:
                retry_after = max(1, int(dq[0] + self._config.window_seconds - now))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )

            dq.append(now)

        return await call_next(request)

