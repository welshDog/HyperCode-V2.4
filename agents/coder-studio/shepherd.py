"""Safety Shepherd gate for coder-studio.

This is the ``can_use_tool`` hook. Every tool the agent wants to run passes
through here first, and **every ambiguous outcome denies**. That inverts the
HyperFlow runner's default (``SAFETY_SHEPHERD_MODE=monitor``, fail-open), which
is safe there only because nothing on that path can write.

Two checks, in order:

1. **Local containment.** A path that resolves outside the worktree is refused
   without asking anyone. Cheaper than a round trip, and correct even if
   Shepherd's manifest is misconfigured.
2. **Shepherd policy.** ``POST /evaluate`` against the live manifest.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from worktree import Worktree, WorktreeEscapeError, resolve_within

ALLOW = "ALLOW"
BLOCK = "BLOCK"
ESCALATE = "ESCALATE"

STUDIO_AGENT = "coder_studio"

_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
_READ_TOOLS = {"Read", "Glob", "Grep"}
_NET_TOOLS = {"WebFetch", "WebSearch"}

# Tools whose target is a path we can contain locally.
_PATH_KEYS = ("file_path", "notebook_path", "path")


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    rule: str
    approval_id: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.decision == ALLOW


def _deny(reason: str, rule: str) -> Verdict:
    return Verdict(BLOCK, reason, rule)


def map_tool_call(tool_name: str, tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Translate an Agent SDK tool call into Shepherd's request vocabulary.

    Returns None for tools we do not recognise — the caller must not guess.
    """
    base = {"agent": STUDIO_AGENT, "context": {"sdk_tool": tool_name}}

    if tool_name in _WRITE_TOOLS:
        return {**base, "category": "file_write", "tool": "file_write", "target": _target_path(tool_input)}

    if tool_name in _READ_TOOLS:
        return {**base, "category": "file_read", "tool": "file_read", "target": _target_path(tool_input)}

    if tool_name == "Bash":
        return {**base, "category": "bash", "tool": "bash", "target": tool_input.get("command", "")}

    if tool_name in _NET_TOOLS:
        url = tool_input.get("url", "")
        return {
            **base,
            "category": "http_external",
            "tool": "http_external",
            "domain": urlparse(url).hostname or "",
        }

    return None


def _target_path(tool_input: dict[str, Any]) -> str:
    for key in _PATH_KEYS:
        value = tool_input.get(key)
        if value:
            return str(value)
    return ""


class ShepherdClient:
    """Thin async client. The httpx client is built once and reused — building
    one per call blocks the event loop for ~284ms (see PRs #309-#314).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"X-Agent-Key": api_key},
        )

    async def evaluate(self, payload: dict[str, Any]) -> Verdict:
        try:
            response = await self._client.post("/evaluate", json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            return _deny(f"Shepherd returned {exc.response.status_code}", "shepherd_error")
        except (httpx.HTTPError, ValueError) as exc:
            return _deny(f"Shepherd unreachable: {exc}", "shepherd_unreachable")

        decision = body.get("decision")
        if decision not in (ALLOW, BLOCK, ESCALATE):
            return _deny(f"Shepherd returned an unreadable verdict: {body!r}", "shepherd_error")

        return Verdict(
            decision=decision,
            reason=body.get("reason", ""),
            rule=body.get("rule", ""),
            approval_id=body.get("approval_id"),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _bash_is_armed() -> bool:
    return os.getenv("STUDIO_ALLOW_BASH", "").strip() in ("1", "true", "yes")


async def check_tool_call(
    shepherd: ShepherdClient,
    worktree: Worktree,
    tool_name: str,
    tool_input: dict[str, Any],
) -> Verdict:
    """Decide whether the agent may run this tool. Denies on any doubt."""
    payload = map_tool_call(tool_name, tool_input)
    if payload is None:
        return Verdict(ESCALATE, f"unrecognised tool '{tool_name}'", "unknown_tool")

    # Bash's target is a shell command, not a path, so Shepherd's blocked_paths
    # globs cannot see `cat backend/.env`. Withhold it until that gap is closed.
    if tool_name == "Bash" and not _bash_is_armed():
        return _deny(
            "bash is withheld in the studio sandbox (set STUDIO_ALLOW_BASH to arm)",
            "bash_withheld",
        )

    target = payload.get("target") or ""
    if payload["category"] in ("file_write", "file_read") and target:
        try:
            resolved = resolve_within(worktree, target)
        except WorktreeEscapeError:
            return _deny(f"'{target}' resolves outside the worktree", "escape_blocked")

        # Shepherd fnmatches this string against blocked_paths ("**/.env") and
        # the agent's file_paths grants. A host-absolute Windows path with
        # backslashes matches neither, so a raw target would walk straight past
        # the secrets globs. Always hand it a worktree-relative POSIX path.
        payload["target"] = resolved.relative_to(worktree.path.resolve()).as_posix()

    return await shepherd.evaluate(payload)
