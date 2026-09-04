"""
governor — Phase 2. The governance-plane nucleus.

Mints signed, scope-bound capability tokens. Holds the kill-switch, the
Ed25519 signing key, the jti replay store, the system lease, and approval
records. Structurally inert: no Docker socket, no DOCKER_HOST, no
crew-orchestrator credential, no LLM/MCP client. See
docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="governor", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "governor"}
