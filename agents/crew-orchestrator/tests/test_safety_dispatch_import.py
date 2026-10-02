"""Regression: _safety_check_dispatch must import its siblings the way uvicorn runs main.

The container starts `uvicorn main:app`, so `main` is a top-level module with no parent
package. A bare `from . import dispatch_capability` raised ImportError and made every
POST /execute return HTTP 500. Tests import `main` the same top-level way, so this fails
without the try/except fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

module_dir = str(Path(__file__).resolve().parents[1])
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

import main as orchestrator_main  # noqa: E402
import safety_client  # noqa: E402


@pytest.mark.asyncio
@pytest.mark.parametrize("agent", ["qa-engineer", "coder-agent"])
async def test_safety_check_dispatch_does_not_raise_import_error(
    monkeypatch: pytest.MonkeyPatch, agent: str
) -> None:
    monkeypatch.setattr(
        orchestrator_main.safety_gate,
        "evaluate_dispatch",
        AsyncMock(return_value={"decision": orchestrator_main.safety_gate.ALLOW}),
    )
    monkeypatch.setattr(
        safety_client,
        "check_dispatch",
        AsyncMock(return_value=SimpleNamespace(decision=orchestrator_main.safety_gate.ALLOW)),
    )
    monkeypatch.setattr(orchestrator_main, "log_event", AsyncMock())

    result = await orchestrator_main._safety_check_dispatch(agent, "build", "task-1", "propose text")

    assert result is None
