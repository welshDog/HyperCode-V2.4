"""Unit tests for the HS-P2c agent-key-authed governance-ledger write path.

No DB — JSONB persistence is proven via the live postgres E2E (same convention
as test_identity_agent.py). The 401/403 header path is covered by
test_agent_auth.py; here we test the endpoint logic and body validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.governance import LedgerWriteRequest, write_ledger


class _FakeDB:
    """Minimal session stub — captures the row that would be persisted."""

    def __init__(self):
        self.added = None
        self.commits = 0

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        obj.id = "00000000-0000-0000-0000-000000000001"


def _body(**overrides):
    base = {
        "agent": "coder_studio",
        "action": "safety.docker",
        "decision": "BLOCK",
        "tool": "container_restart",
        "payload": {"rule": "docker.write_denied", "id": "evt-1"},
    }
    base.update(overrides)
    return LedgerWriteRequest(**base)


def test_write_ledger_records_verdict():
    db = _FakeDB()
    result = write_ledger(_body(), db=db, agent_key={"agent_name": "safety-shepherd"})

    assert result == {"id": "00000000-0000-0000-0000-000000000001", "status": "recorded"}
    row = db.added
    assert row.agent_name == "coder_studio"
    assert row.action == "safety.docker"
    assert row.decision == "BLOCK"
    assert row.tool_used == "container_restart"
    assert row.user_id == "system"  # default when the writer has no user context
    assert row.approved_by == "safety-shepherd"  # defaults to the calling key
    assert row.payload["rule"] == "docker.write_denied"
    assert db.commits == 1


def test_write_ledger_keeps_explicit_approved_by():
    db = _FakeDB()
    write_ledger(
        _body(approved_by="lyndz"),
        db=db,
        agent_key={"agent_name": "safety-shepherd"},
    )
    assert db.added.approved_by == "lyndz"


def test_write_ledger_body_requires_core_fields():
    with pytest.raises(ValidationError):
        LedgerWriteRequest(agent="x")  # action + decision missing
