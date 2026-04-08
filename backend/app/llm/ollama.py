from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time

import httpx


@dataclass(frozen=True)
class OllamaModelCandidate:
    name: str
    size_bytes: int
    quantization_level: str
    parameter_size: str


def _quantization_rank(quantization_level: str) -> int:
    preferred = [
        "Q4_0",
        "Q4_K_M",
        "Q4_K_S",
        "Q4_K",
        "Q5_0",
        "Q5_K_M",
        "Q5_K_S",
        "Q5_K",
        "Q6_K",
        "Q8_0",
    ]
    try:
        return preferred.index(quantization_level)
    except ValueError:
        return len(preferred)


def _preferred_rank(model_name: str, preferred_patterns: list[str]) -> int:
    lower = model_name.lower()
    for index, pattern in enumerate(preferred_patterns):
        if not pattern:
            continue
        if pattern.lower() in lower:
            return index
    return len(preferred_patterns)


def select_best_ollama_model(
    tags_payload: dict[str, Any],
    *,
    preferred_patterns: list[str],
    max_size_mb: int,
) -> str | None:
    models_raw = tags_payload.get("models")
    if not isinstance(models_raw, list):
        return None

    max_size_bytes = max_size_mb * 1024 * 1024
    candidates: list[OllamaModelCandidate] = []

    for raw in models_raw:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            continue

        size = raw.get("size")
        if not isinstance(size, int):
            size = 0

        details = raw.get("details")
        if not isinstance(details, dict):
            details = {}

        quant = details.get("quantization_level")
        if not isinstance(quant, str):
            quant = ""

        param = details.get("parameter_size")
        if not isinstance(param, str):
            param = ""

        if size and size > max_size_bytes:
            continue

        candidates.append(
            OllamaModelCandidate(
                name=name,
                size_bytes=size,
                quantization_level=quant,
                parameter_size=param,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda c: (
            _preferred_rank(c.name, preferred_patterns),
            c.size_bytes or (1024**5),
            _quantization_rank(c.quantization_level),
            c.name,
        )
    )
    return candidates[0].name


class OllamaModelResolver:
    def __init__(
        self,
        *,
        ollama_host: str,
        preferred_patterns: list[str],
        max_size_mb: int,
        refresh_seconds: int,
    ) -> None:
        self.ollama_host = ollama_host.rstrip("/")
        self.preferred_patterns = preferred_patterns
        self.max_size_mb = max_size_mb
        self.refresh_seconds = refresh_seconds
        self._cached_model: str | None = None
        self._cached_at: float | None = None

    async def resolve(self, client: httpx.AsyncClient) -> str | None:
        now = time.time()
        if self._cached_model and self._cached_at and (now - self._cached_at) < self.refresh_seconds:
            return self._cached_model

        response = await client.get(f"{self.ollama_host}/api/tags")
        response.raise_for_status()
        selected = select_best_ollama_model(
            response.json(),
            preferred_patterns=self.preferred_patterns,
            max_size_mb=self.max_size_mb,
        )
        if selected:
            self._cached_model = selected
            self._cached_at = now
        return selected

