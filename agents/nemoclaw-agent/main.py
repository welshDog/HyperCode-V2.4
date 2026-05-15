"""nemoclaw-agent — autonomous code-health scanner for HyperCode V2.4.

Endpoints:
  GET  /health    — liveness + dependency status (unauthenticated)
  POST /scan      — run a code-health scan, return score + grade + top issues
  GET  /history   — last N scans (from Postgres if available, else empty)

Auth: every request except /health requires X-Agent-Key or X-API-Key matching
HYPERCODE_API_KEY env. No secret values are ever surfaced in responses.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from analyzer import NemoClaw
from db import close_pool, get_pool, insert_scan, recent_scans

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nemoclaw.main")

app = FastAPI(title="nemoclaw-agent", version="0.1.0")


@app.middleware("http")
async def _agent_auth(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)

    expected = _expected_api_key()
    if not expected:
        return JSONResponse(status_code=503, content={"detail": "Agent API key not configured"})

    provided = request.headers.get("x-agent-key") or request.headers.get("x-api-key")
    if not provided or not compare_digest(str(provided), expected):
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


def _read_secret_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _expected_api_key() -> str:
    """Resolve API key — mounted secret file first (more secure), then env var."""
    file_path = os.getenv("HYPERCODE_API_KEY_FILE") or os.getenv("AGENT_API_KEY_FILE", "")
    if file_path:
        from_file = _read_secret_file(file_path)
        if from_file:
            return from_file
    return (os.getenv("HYPERCODE_API_KEY") or os.getenv("AGENT_API_KEY") or "").strip()


def _workspace() -> str:
    return os.getenv("WORKSPACE_PATH", "/workspace")


def _default_targets() -> list[str]:
    raw = os.getenv("NEMOCLAW_SCAN_TARGETS", "backend,agents")
    return [t.strip() for t in raw.split(",") if t.strip()]


class ScanRequest(BaseModel):
    targets: list[str] | None = Field(default=None, description="Subdirs to scan; defaults to NEMOCLAW_SCAN_TARGETS env")


@app.post("/scan")
async def scan(body: ScanRequest | None = None) -> dict[str, object]:
    targets = (body.targets if body and body.targets else None) or _default_targets()
    workspace = _workspace()
    nemo = NemoClaw(scan_root=workspace, scan_targets=targets)

    # Scanner runs subprocesses (ruff, detect-secrets) — push to thread to keep loop responsive.
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, nemo.scan)

    scan_id = str(uuid.uuid4())
    persisted = await insert_scan(
        scan_id=scan_id,
        score=result.score,
        grade=result.grade,
        counts=result.counts,
        total_files=result.total_files,
        top_issues=result.top_issues,
    )

    return {
        "scan_id": scan_id,
        "persisted": persisted,
        "score": result.score,
        "grade": result.grade,
        "grade_label": result.grade_label,
        "grade_emoji": result.grade_emoji,
        "total_files": result.total_files,
        "counts": result.counts,
        "top_issues": result.top_issues,
        "scanned_at": result.scanned_at,
        "scan_targets": result.scan_targets,
    }


@app.get("/history")
async def history(limit: int = 10) -> dict[str, object]:
    limit = max(1, min(100, limit))
    rows = await recent_scans(limit=limit)
    return {"count": len(rows), "scans": rows}


@app.get("/health")
async def health() -> dict[str, object]:
    workspace = _workspace()
    workspace_ok = os.path.isdir(workspace)
    pool = await get_pool()
    db_ok = pool is not None
    api_key_configured = bool(_expected_api_key())
    return {
        "status": "ok",
        "service": "nemoclaw-agent",
        "workspace": workspace,
        "workspace_ok": workspace_ok,
        "db_connected": db_ok,
        "api_key_configured": api_key_configured,
    }


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_pool()
