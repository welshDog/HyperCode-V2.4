"""safety_client.check_dispatch must send the Shepherd the exact same request
body as safety_gate.evaluate_dispatch.

This is the property card (b)'s canary depends on: run both paths in parallel,
compare verdicts, flip enforcement only once they agree. If the two bodies
drift, the canary silently compares apples to oranges — so pin it here, not in
a docstring. The shared contract test only checks shape against its own
literals; this checks the two real implementations against each other.
"""
import asyncio

import pytest

import safety_client
import safety_gate


class _CapturingClient:
    def __init__(self):
        self.body = None

    async def post(self, url, json=None, headers=None):
        self.body = json

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"decision": "ALLOW", "reason": "ok"}

        return _Resp()


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(safety_gate, "_client", None)
    monkeypatch.setattr(safety_client, "_client", None)
    # evaluate_dispatch short-circuits before building the body when mode is
    # "off"; force a mode that exercises the body-building path.
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "monitor")
    yield


def test_check_dispatch_body_matches_evaluate_dispatch_body():
    agent, task_type, task_id, description = "qa-engineer", "test", "task-77", "y" * 400

    gate_cap = _CapturingClient()
    client_cap = _CapturingClient()

    async def _drive():
        safety_gate._client = gate_cap
        await safety_gate.evaluate_dispatch(agent, task_type, task_id, description)
        safety_client._client = client_cap
        await safety_client.check_dispatch(
            safety_client.DispatchRequest(
                agent=agent, tool=task_type, task_id=task_id, description=description
            )
        )

    asyncio.run(_drive())

    assert gate_cap.body is not None and client_cap.body is not None
    assert client_cap.body == gate_cap.body
