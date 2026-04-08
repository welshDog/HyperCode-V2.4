# pylint: disable=broad-exception-caught
# pyright: reportMissingImports=false
from __future__ import annotations

from typing import AsyncIterator, Dict, Tuple
import json

import aiohttp  # type: ignore


async def _iter_sse(resp: aiohttp.ClientResponse) -> AsyncIterator[Tuple[str, str]]:
    event = "message"
    data_lines: list[str] = []

    while True:
        raw = await resp.content.readline()
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if line.startswith(":"):
            continue
        if line == "":
            if data_lines:
                yield (event, "\n".join(data_lines))
            event = "message"
            data_lines = []
            continue
        if line.startswith("event:"):
            event = line[len("event:") :].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())


async def stream_generate(
    *,
    base_url: str,
    token: str,
    prompt: str,
    max_tokens: int = 512,
    timeout_read_s: int = 300,
) -> AsyncIterator[Tuple[str, Dict]]:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url.rstrip('/')}/generate",
            headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            json={"prompt": prompt, "stream": True, "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=timeout_read_s),
        ) as resp:
            if resp.status != 200:
                yield ("error", {"status": resp.status})
                return

            async for ev, data in _iter_sse(resp):
                try:
                    obj = json.loads(data) if data else {}
                    if isinstance(obj, dict):
                        yield (ev, obj)
                    else:
                        yield (ev, {"value": obj})
                except Exception:
                    yield (ev, {"raw": data})

