# agents/mission-executor/test_basic.py
"""
Basic tests for mission-executor components.

These used to catch every exception and return False, so pytest reported a pass even when an
import or a model was broken. They now assert, so a failure is a failure.

Run: cd agents/mission-executor && python -m pytest -q
"""

import sys

import pytest

from models import ExecutionRequest, ExecutionResult, ExecutionStatus


def test_imports():
    """The main components import."""
    from agent_delegator import AgentDelegator  # noqa: F401
    from main import app  # noqa: F401


def test_models():
    """Models can be instantiated and keep their values."""
    request = ExecutionRequest(
        mission_id="test_001",
        goal="Test goal",
        plan={"requested_actions": []},
    )
    assert request.mission_id == "test_001"
    assert request.goal == "Test goal"
    assert request.requested_at is None

    result = ExecutionResult(mission_id="test_001", status=ExecutionStatus.COMPLETED)
    assert result.mission_id == "test_001"
    assert result.status == ExecutionStatus.COMPLETED
    assert result.executed_actions == []
    assert result.agent_outputs == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
