"""Shared behavioural contract for the strict fail-closed dispatch client.

crew-orchestrator and fleet-controller each ship their OWN
``safety_client.py`` (per-agent, in-image, no shared runtime bytes — see the
card (a) supersession note in the safety session report). This module is the
single source of truth for the *contract* those two implementations must
both satisfy, so drift between them fails a test instead of shipping.

Usage — one thin test per suite::

    import safety_client
    from safety_contract import assert_strict_client_contract

    def test_strict_dispatch_client_contract():
        assert_strict_client_contract(safety_client)

The client module under test must expose:

* ``SafetyResult``      — frozen dataclass:
                          decision, reason, rule, category,
                          shepherd_available, fail_closed
* ``_FAIL_CLOSED``      — a frozen ``SafetyResult`` singleton returned on every
                          failure branch (one identity to assert against)
* ``DispatchRequest``   — dataclass carrying: agent, tool, task_id, description
* ``check_dispatch(dispatch) -> SafetyResult``  — async, no mode knob
* module-level ``_client`` — the httpx client slot, swappable for a fake
"""
from __future__ import annotations

import asyncio
import dataclasses
import inspect

import httpx


# --------------------------------------------------------------------------- #
# fake transport
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, status_code=200, payload=None, json_exc=None):
        self.status_code = status_code
        self._payload = payload
        self._json_exc = json_exc

    def json(self):
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


class _FakeClient:
    def __init__(self, *, resp=None, post_exc=None):
        self._resp = resp
        self._post_exc = post_exc
        self.calls = []

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self._post_exc is not None:
            raise self._post_exc
        return self._resp


def _run(client_module, dispatch, *, resp=None, post_exc=None):
    fake = _FakeClient(resp=resp, post_exc=post_exc)
    client_module._client = fake
    try:
        result = asyncio.run(client_module.check_dispatch(dispatch))
    finally:
        client_module._client = None
    return result, fake


# --------------------------------------------------------------------------- #
# the contract
# --------------------------------------------------------------------------- #
def assert_strict_client_contract(client_module) -> None:
    """Assert ``client_module`` satisfies the strict dispatch-client contract."""
    _assert_surface(client_module)
    _assert_no_mode_knob(client_module)
    _assert_no_caller_capability(client_module)
    _assert_fail_closed_singleton(client_module)

    make = _dispatch_factory(client_module)

    _assert_failure_branches_fail_closed(client_module, make)
    _assert_shepherd_verdicts_pass_through(client_module, make)
    _assert_request_shape(client_module, make)


# --------------------------------------------------------------------------- #
# surface / structure
# --------------------------------------------------------------------------- #
_RESULT_FIELDS = {
    "decision",
    "reason",
    "rule",
    "category",
    "shepherd_available",
    "fail_closed",
}


def _assert_surface(m) -> None:
    for name in ("SafetyResult", "_FAIL_CLOSED", "DispatchRequest", "check_dispatch"):
        assert hasattr(m, name), f"{m.__name__} is missing {name!r}"

    assert inspect.iscoroutinefunction(
        m.check_dispatch
    ), "check_dispatch must be async"

    params = dataclasses.fields(m.SafetyResult)
    assert {f.name for f in params} == _RESULT_FIELDS, (
        f"SafetyResult fields {sorted(f.name for f in params)} "
        f"!= {sorted(_RESULT_FIELDS)}"
    )
    assert m.SafetyResult.__dataclass_params__.frozen, "SafetyResult must be frozen"

    dfields = {f.name for f in dataclasses.fields(m.DispatchRequest)}
    for need in ("agent", "tool", "task_id", "description"):
        assert need in dfields, f"DispatchRequest missing field {need!r}"


def _assert_no_mode_knob(m) -> None:
    # The strict route is unconditional: no _mode() helper, and the
    # safety_gate off/observe env var must not influence it. (Prose in a
    # docstring contrasting this client with safety_gate is fine — only the
    # behaviour is constrained.)
    assert not hasattr(m, "_mode"), "strict client must not have a _mode() knob"
    assert "SAFETY_SHEPHERD_MODE" not in inspect.getsource(m), (
        "strict client must not read SAFETY_SHEPHERD_MODE (function or module-level)"
    )


def _assert_no_caller_capability(m) -> None:
    sig = inspect.signature(m.check_dispatch)
    names = list(sig.parameters)
    assert names == ["dispatch"], (
        f"check_dispatch({', '.join(names)}) — must take exactly one arg 'dispatch'"
    )


def _assert_fail_closed_singleton(m) -> None:
    fc = m._FAIL_CLOSED
    assert isinstance(fc, m.SafetyResult)
    assert fc.decision == "BLOCK"
    assert fc.fail_closed is True
    assert fc.shepherd_available is False


# --------------------------------------------------------------------------- #
# behaviour
# --------------------------------------------------------------------------- #
def _dispatch_factory(m):
    def make():
        return m.DispatchRequest(
            agent="qa-engineer",
            tool="run_tests",
            task_id="task-abc",
            description="x" * 500,
        )

    return make


def _assert_failure_branches_fail_closed(m, make) -> None:
    cases = {
        "timeout": dict(post_exc=httpx.TimeoutException("timed out")),
        "connect-error": dict(post_exc=httpx.ConnectError("shepherd down")),
        "non-200": dict(resp=_FakeResp(status_code=503, payload={"decision": "ALLOW"})),
        "malformed-json": dict(resp=_FakeResp(json_exc=ValueError("not json"))),
        "non-dict-json": dict(resp=_FakeResp(payload=["ALLOW"])),
        "missing-decision": dict(resp=_FakeResp(payload={"reason": "no verdict"})),
    }
    for label, kw in cases.items():
        result, _ = _run(m, make(), **kw)
        assert result is m._FAIL_CLOSED, f"{label}: expected the _FAIL_CLOSED singleton"
        assert result.decision == "BLOCK", f"{label}: decision"
        assert result.fail_closed is True, f"{label}: fail_closed"
        assert result.shepherd_available is False, f"{label}: shepherd_available"


def _assert_shepherd_verdicts_pass_through(m, make) -> None:
    for raw, expected in (("allow", "ALLOW"), ("escalate", "ESCALATE"), ("block", "BLOCK")):
        payload = {"decision": raw, "reason": "verdict", "rule": "r1", "category": "generic"}
        result, _ = _run(m, make(), resp=_FakeResp(payload=payload))
        assert result.decision == expected, f"{raw}: decision -> {expected}"
        assert result.shepherd_available is True, f"{raw}: shepherd_available"
        assert result.fail_closed is False, f"{raw}: fail_closed"
        assert result is not m._FAIL_CLOSED, (
            f"{raw}: a real Shepherd verdict must not be the fail-closed singleton"
        )


def _assert_request_shape(m, make) -> None:
    """The Shepherd payload must mirror safety_gate.evaluate_dispatch exactly."""
    result, fake = _run(
        m, make(), resp=_FakeResp(payload={"decision": "allow", "reason": "ok"})
    )
    assert len(fake.calls) == 1, "check_dispatch must POST exactly once on the happy path"
    body = fake.calls[0]["json"]
    assert body["agent"] == "qa-engineer"
    assert body["category"] == "generic", "category is fixed to 'generic'"
    assert body["tool"] == "run_tests"
    assert body["target"] is None
    assert body["domain"] is None
    ctx = body["context"]
    assert isinstance(ctx.get("source"), str) and ctx["source"], "context.source"
    assert ctx["task_id"] == "task-abc"
    assert ctx["description"] == "x" * 200, "description truncated to 200 chars"
