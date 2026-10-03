"""PROOF-ONLY harness for scripts/prove-crew-local.py — never deploy this.

Runs the REAL hypercode-core app (real operator API, real HyperFlow runner, real boot-time recovery)
on a throwaway sqlite file with two seeded users (1 = superuser, 2 = normal). Humans authenticate with a
REAL JWT through the real code path; only the agent-key lookup (which needs Postgres) is replaced: any
``X-Agent-Key`` header is accepted as the proof MCP agent.
Run with:  uvicorn crew_proof_harness:app --app-dir scripts   (cwd = backend/, PYTHONPATH=.)
"""

import sqlalchemy.ext.asyncio as _sa_async
from fastapi import Request

# core derives an asyncpg engine from the DB URL; on sqlite use aiosqlite and drop the pool arguments.
_real_create_async_engine = _sa_async.create_async_engine


def _create_async_engine(url, **kw):
    url = str(url)
    if url.startswith("sqlite:"):
        url = url.replace("sqlite:", "sqlite+aiosqlite:", 1)
        for k in ("pool_size", "max_overflow", "pool_recycle", "pool_timeout"):
            kw.pop(k, None)
    return _real_create_async_engine(url, **kw)


_sa_async.create_async_engine = _create_async_engine

from app.db.base_class import Base
from app.db.session import engine
import importlib

from app.main import app as _core_app

importlib.import_module("app.models.models")  # registers the tables

Base.metadata.create_all(bind=engine)


from app.db.session import SessionLocal
from app.middleware.agent_auth import get_agent_from_key
from app.models.models import User


async def proof_agent(request: Request):
    """Agent-key auth stand-in (the real one needs Postgres): any X-Agent-Key is the proof MCP agent."""
    return {"agent_name": "proof-mcp"} if request.headers.get("x-agent-key") else None


def _seed_users() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(id=1, email="proof-super@example.com", hashed_password="x", is_superuser=True, is_active=True))
            db.add(User(id=2, email="proof-normal@example.com", hashed_password="x", is_superuser=False, is_active=True))
            db.commit()
    finally:
        db.close()


_seed_users()
# Only the agent-key lookup is replaced. Human auth is the REAL path: a real JWT, a real user row, the real
# superuser check, and a real 401 when there are no credentials at all.
_core_app.dependency_overrides[get_agent_from_key] = proof_agent
app = _core_app  # the name uvicorn imports
