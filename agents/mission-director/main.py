# agents/mission-director/main.py
"""
mission-director -- Phase 1.

Health-only in this task; POST /v1/plan lands in Task 3. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="mission-director", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "mission-director"}
