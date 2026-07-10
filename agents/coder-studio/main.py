"""coder-studio — the HyperStudio write path (port 8087).

A human hands the studio a task. The service:

  1. cuts a throwaway git worktree off the current HEAD,
  2. runs a Claude agent inside it, gating every tool call through Safety
     Shepherd (fail-closed),
  3. streams the agent's messages and each Shepherd decision over SSE,
  4. shows the resulting diff, and lands it on the base branch only when the
     human clicks merge.

Nothing reaches the working tree until a merge is requested. Auth is the shared
``X-Agent-Key`` used across the agent mesh.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_runner import DEFAULT_MODEL, GateShadowedError, run_agent
from sessions import Session, SessionStore, Status
from shepherd import ShepherdClient
from worktree import (
    WorktreeError,
    capture_diff,
    create_worktree,
    discard_worktree,
    merge_worktree,
)

SHEPHERD_URL = os.getenv("SAFETY_SHEPHERD_URL", "http://safety-shepherd:8096")


def workspace_root() -> Path:
    """The repo the studio operates on. Read at call time, not import time, so
    the value is never frozen before the environment is configured."""
    return Path(os.getenv("WORKSPACE_ROOT", "/workspace"))


app = FastAPI(title="coder-studio", version="0.1.0")
store = SessionStore()
_shepherd: ShepherdClient | None = None
_tasks: set[asyncio.Task] = set()


def shepherd() -> ShepherdClient:
    global _shepherd
    if _shepherd is None:
        _shepherd = ShepherdClient(SHEPHERD_URL, _api_key())
    return _shepherd


def _api_key() -> str:
    file_path = os.getenv("HYPERCODE_API_KEY_FILE", "")
    if file_path and Path(file_path).exists():
        return Path(file_path).read_text(encoding="utf-8").strip()
    return (os.getenv("HYPERCODE_API_KEY") or os.getenv("API_KEY") or "dev-master-key").strip()


async def require_key(x_agent_key: str | None = Header(default=None)) -> None:
    if x_agent_key != _api_key():
        raise HTTPException(status_code=401, detail="bad or missing X-Agent-Key")


# ── models ──────────────────────────────────────────────────────────────────
class StartRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    slug: str = "task"
    model: str | None = None


class SessionView(BaseModel):
    id: str
    status: str
    prompt: str
    diff: str | None = None
    merge_sha: str | None = None

    @classmethod
    def of(cls, s: Session) -> "SessionView":
        return cls(id=s.id, status=s.status.value, prompt=s.prompt, diff=s.diff, merge_sha=s.merge_sha)


# ── the agent run ───────────────────────────────────────────────────────────
async def _drive_agent(session: Session, model: str | None, slug: str = "task") -> None:
    """Run the agent, streaming events into the session. Never raises."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

    try:
        # Create the sandbox here, not in the POST handler — on a big repo the
        # worktree checkout takes 10s+ and must not block session creation.
        if session.worktree is None:
            session.add_event("status", {"status": "preparing sandbox"})
            session.worktree = await asyncio.to_thread(create_worktree, workspace_root(), slug)

        # The user can discard while the sandbox is still being built. If they
        # did, clean up the worktree we just made and stop — don't run the agent.
        if session.status in (Status.DISCARDED, Status.MERGED):
            with contextlib.suppress(WorktreeError):
                await asyncio.to_thread(discard_worktree, session.worktree)
            return

        session.set_status(Status.RUNNING)
        async for message in run_agent(
            session.worktree,
            shepherd(),
            session.prompt,
            model=model,
            on_decision=lambda d: session.add_event("decision", d),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        session.add_event("message", {"role": "assistant", "text": block.text})
                    elif isinstance(block, ToolUseBlock):
                        session.add_event(
                            "message", {"role": "tool_use", "tool": block.name, "input": block.input}
                        )
            elif isinstance(message, ResultMessage):
                session.add_event(
                    "message", {"role": "result", "cost_usd": getattr(message, "total_cost_usd", None)}
                )

        session.diff = await asyncio.to_thread(capture_diff, session.worktree)
        session.set_status(Status.REVIEW)
    except GateShadowedError as exc:
        session.add_event("error", {"error": f"refused to run ungated agent: {exc}"})
        session.set_status(Status.FAILED)
    except Exception as exc:  # noqa: BLE001 — a crashed run must not wedge the service
        session.add_event("error", {"error": str(exc)})
        session.set_status(Status.FAILED)


# ── routes ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "coder-studio", "model": os.getenv("STUDIO_MODEL", DEFAULT_MODEL)}


@app.post("/sessions", response_model=SessionView, dependencies=[Depends(require_key)])
async def start_session(body: StartRequest) -> SessionView:
    # Return immediately. The worktree checkout (slow on a big repo) and the
    # agent run happen in the background and stream over /events.
    session = store.create(body.prompt)
    task = asyncio.create_task(_drive_agent(session, body.model, body.slug))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return SessionView.of(session)


@app.get("/sessions/{session_id}", response_model=SessionView, dependencies=[Depends(require_key)])
async def get_session(session_id: str) -> SessionView:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    return SessionView.of(session)


_TERMINAL = (Status.REVIEW, Status.MERGED, Status.DISCARDED, Status.FAILED)


async def sse_events(session: Session, poll: float = 0.25) -> AsyncIterator[str]:
    """Replay every event, then tail live ones until the run reaches a terminal
    state. Replaying from the start means a late subscriber still sees the whole
    run."""
    cursor = 0
    while True:
        while cursor < len(session.events):
            event = session.events[cursor]
            cursor += 1
            yield f"event: {event.kind}\ndata: {json.dumps(event.data)}\n\n"
        if session.status in _TERMINAL and cursor >= len(session.events):
            yield "event: end\ndata: {}\n\n"
            return
        await asyncio.sleep(poll)


@app.get("/sessions/{session_id}/events", dependencies=[Depends(require_key)])
async def stream_events(session_id: str) -> StreamingResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    return StreamingResponse(sse_events(session), media_type="text/event-stream")


@app.get("/sessions/{session_id}/diff", dependencies=[Depends(require_key)])
async def get_diff(session_id: str) -> dict[str, Any]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    return {"id": session.id, "status": session.status.value, "diff": session.diff or ""}


@app.post("/sessions/{session_id}/merge", response_model=SessionView, dependencies=[Depends(require_key)])
async def merge(session_id: str, idempotency_key: str | None = Header(default=None)) -> SessionView:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")

    if session.status == Status.MERGED:
        return SessionView.of(session)  # idempotent replay
    if not session.is_mergeable:
        raise HTTPException(status_code=409, detail=f"session is {session.status.value}, not reviewable")

    message = f"feat(studio): {session.prompt[:60]}"
    try:
        sha = await asyncio.to_thread(merge_worktree, session.worktree, message)
    except WorktreeError as exc:
        raise HTTPException(status_code=409, detail=f"merge failed: {exc}") from exc

    session.merge_sha = sha
    session.set_status(Status.MERGED)
    with contextlib.suppress(WorktreeError):
        await asyncio.to_thread(discard_worktree, session.worktree)
    return SessionView.of(session)


@app.post("/sessions/{session_id}/discard", response_model=SessionView, dependencies=[Depends(require_key)])
async def discard(session_id: str) -> SessionView:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    if session.status in (Status.MERGED, Status.DISCARDED):
        return SessionView.of(session)

    # A run can fail before its worktree exists (e.g. sandbox creation failed).
    if session.worktree is not None:
        with contextlib.suppress(WorktreeError):
            await asyncio.to_thread(discard_worktree, session.worktree)
    session.set_status(Status.DISCARDED)
    return SessionView.of(session)
