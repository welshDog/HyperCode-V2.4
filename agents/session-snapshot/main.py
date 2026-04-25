from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from snapshot_writer import get_changed_files, write_session_md, workspace_from_env

app = FastAPI(title="Session Snapshot Agent", version="1.0.0")


class SnapshotResponse(BaseModel):
    status: str
    path: str


class SnapshotRequest(BaseModel):
    output_filename: str = Field(default="SESSION.md", min_length=1, max_length=200)


@dataclass
class IdleState:
    last_status_hash: str | None = None
    last_status_change_monotonic: float = 0.0
    last_written_monotonic: float = 0.0


_idle_state = IdleState()
_poll_task: asyncio.Task[None] | None = None


def _hash_lines(lines: list[str]) -> str:
    joined = "\n".join(lines).encode("utf-8", errors="ignore")
    return hashlib.sha256(joined).hexdigest()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "session-snapshot"}


@app.post("/snapshot", response_model=SnapshotResponse)
async def snapshot(req: SnapshotRequest) -> SnapshotResponse:
    workspace = workspace_from_env()
    if not workspace.exists():
        raise HTTPException(status_code=500, detail=f"WORKSPACE_PATH not found: {workspace}")

    output_path = (workspace / req.output_filename).resolve()
    written = write_session_md(workspace_path=workspace, output_path=output_path)
    return SnapshotResponse(status="ok", path=str(written))


async def _poll_idle_loop() -> None:
    poll_seconds = max(30, _env_int("SNAPSHOT_POLL_SECONDS", 300))
    idle_minutes = max(5, _env_int("SNAPSHOT_IDLE_MINUTES", 30))
    idle_seconds = idle_minutes * 60

    workspace = workspace_from_env()
    if not workspace.exists():
        return

    _idle_state.last_status_change_monotonic = time.monotonic()

    while True:
        try:
            changed = get_changed_files(workspace)
            digest = _hash_lines(changed)
            now = time.monotonic()

            if _idle_state.last_status_hash is None:
                _idle_state.last_status_hash = digest
                _idle_state.last_status_change_monotonic = now
            elif digest != _idle_state.last_status_hash:
                _idle_state.last_status_hash = digest
                _idle_state.last_status_change_monotonic = now

            idle_for = now - _idle_state.last_status_change_monotonic
            should_write = (
                idle_for >= idle_seconds and _idle_state.last_written_monotonic < _idle_state.last_status_change_monotonic
            )
            if should_write:
                write_session_md(workspace_path=workspace)
                _idle_state.last_written_monotonic = now
        except Exception:
            pass

        await asyncio.sleep(poll_seconds)


@app.on_event("startup")
async def _startup() -> None:
    global _poll_task
    _poll_task = asyncio.create_task(_poll_idle_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _poll_task
    if _poll_task is not None:
        _poll_task.cancel()
        _poll_task = None
