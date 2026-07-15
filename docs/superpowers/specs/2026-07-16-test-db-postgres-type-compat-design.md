# Test DB Postgres-Type Compatibility — Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unblock the backend pytest suite, which currently errors on every test that touches the database, by making three models' Postgres-only column types (`JSONB`, `UUID` + `gen_random_uuid()` default) compile against the SQLite engine `conftest.py` uses for tests — without changing production (Postgres) behavior at all.

## Problem

`backend/tests/conftest.py` builds the test database against SQLite (`sqlite:///./test.db`) for speed and zero external dependencies. Three model files import types from `sqlalchemy.dialects.postgresql`, which are Postgres-specific and have no SQLite compiler support:

| File | Column | Type | Issue |
|---|---|---|---|
| `backend/app/models/governance.py` | `GovernanceLedger.payload` | `JSONB` | No `visit_JSONB` on SQLite compiler |
| `backend/app/models/governance.py` | `GovernanceLedger.id` | `UUID(as_uuid=False)` + `server_default=text("gen_random_uuid()")` | No `visit_UUID` on SQLite compiler; `gen_random_uuid()` is a Postgres function, doesn't exist in SQLite |
| `backend/app/models/hyperflow.py` | `HyperFlowRun.state` | `JSONB` | Same as above |
| `backend/app/models/identity.py` | `BROskiIdentityAgent.state` | `JSONB` | Same as above |

The `db` pytest fixture (`conftest.py`) calls `Base.metadata.create_all(bind=engine)` before every test. Because model imports register all tables on `Base.metadata` regardless of which test is running, this call fails with `AttributeError: 'SQLiteTypeCompiler' object has no attribute 'visit_JSONB'` (or the UUID equivalent) for **any** test using the `db` or `client` fixtures — confirmed for all 13 tests in `test_api_endpoints.py`; almost certainly also affects `test_governance_write.py`, `test_hyperflow.py`, and `test_identity_agent.py` since they exercise these same models.

This is a test-infrastructure bug, not a production bug — Postgres has always compiled these types fine. It exists purely because the test suite's SQLite engine diverges from production's Postgres engine on these 4 columns.

## Fix

Use SQLAlchemy's standard cross-dialect idiom, `Type.with_variant(other_type, "dialect_name")`, which tells SQLAlchemy "use this DDL/compiler behavior for dialect X, and the original type everywhere else." This is additive — it changes nothing about how the column behaves under Postgres.

**JSONB columns (3 files, 1 line each):**
```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
    JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
)
```

**UUID column (`governance.py`, 1 column):**
```python
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID

id: Mapped[str] = mapped_column(
    UUID(as_uuid=False).with_variant(String(36), "sqlite"),
    primary_key=True,
    default=lambda: str(uuid.uuid4()),
    server_default=text("gen_random_uuid()"),
)
```
The added `default=` is a Python-side value generator: SQLAlchemy computes it and includes it in every ORM-issued `INSERT`, on **any** dialect, so SQLite tests get a real UUID string without needing `gen_random_uuid()`. The pre-existing `server_default` is untouched and keeps acting as a DB-level fallback in Postgres for any raw-SQL insert path that bypasses the ORM.

## Testing

1. Run the four known-affected files directly and confirm they pass:
   `test_api_endpoints.py`, `test_governance_write.py`, `test_hyperflow.py`, `test_identity_agent.py`
2. Run the full `backend/tests/` suite (`PYTHONUTF8=1` — a separate, pre-existing Windows-only quirk in how `starlette.Config` reads `.env`; unrelated to this fix, out of scope) and confirm no regressions and no new errors.
3. No new tests are required — this fix makes existing tests pass; it doesn't add new behavior to verify.

## Out of Scope

- A full audit of every model in `backend/app/models/` for other Postgres/SQLite type mismatches. This plan fixes only the 4 columns confirmed broken by the actual test failures observed.
- The `PYTHONUTF8` Windows-encoding workaround for running pytest at all. Real, pre-existing, separately worked around — not part of this fix.
- Switching the test suite to a real Postgres backend. Rejected as heavier (external dependency, slower local iteration) with no benefit over the targeted type-variant fix for this specific problem.

## Global Constraints

- Branch: create off `origin/main` (confirm exact name in the implementation plan).
- Commit prefixes: `fix:` / `test:` / `docs:` only for this work.
- Python: absolute imports, 4-space indent (repo convention).
- Zero behavior change for Postgres/production — every change here is additive (`.with_variant()`, an extra `default=` alongside the existing `server_default`).
- Run backend tests from the repo root with `PYTHONUTF8=1 python -m pytest backend/tests/<file> -v` (Windows dev-environment note, not a code change).
