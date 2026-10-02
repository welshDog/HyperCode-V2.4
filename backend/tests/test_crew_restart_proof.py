"""HyperCrew Day 5 — SANDBOX proof (not the live proof): real DB rows, real runner, real recovery code.

What is real: the operator API, ``HyperFlowRunner``, ``recover_runs()``, the Postgres-shaped run row
(sqlite here), the approval/idempotency/slot logic, the AG-UI event mapper and the Calm Card.
What is faked: the crew-orchestrator HTTP hop (``dispatch_to_agent``), Redis fan-out and Safety Shepherd.
"Restart" = the runner task is cancelled exactly like an event-loop shutdown (run row left open) and
``recover_runs()`` re-attaches it — the same function core calls at boot. The true container restart
is proved by ``scripts/prove-crew.py`` against a live stack.
"""

import asyncio
import time

import pytest
from sqlalchemy.orm import sessionmaker

import app.agents.hyperflow_runner as runner_mod
import app.broski_operator.recovery as recovery_mod
from app.crew import dispatch as crew_dispatch
from app.crew import tools as crew_tools
from app.models.governance import GovernanceLedger
from tests.test_crew_operator_api import GOAL, KEY, _as, _fake_dispatch

BASE = "/api/v1/operator"


@pytest.fixture
def real_runner(db, monkeypatch, slot_gate):
    """Point every runner-side DB use at the test database; silence only the network fan-out."""
    factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
    for mod in (runner_mod, recovery_mod, crew_tools):
        monkeypatch.setattr(mod, "SessionLocal", factory)

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_publish", noop)
    monkeypatch.setattr(runner_mod.HyperFlowRunner, "_publish_approval_request", noop)
    monkeypatch.setattr(runner_mod, "APPROVAL_POLL_SECONDS", 0.05)
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", _fake_dispatch())
    return factory


def wait_for(client, task_id, status, node=None, timeout=15.0):
    end, last = time.time() + timeout, None
    while time.time() < end:
        body = client.get(f"{BASE}/tasks/{task_id}").json()
        last = body["status"]
        gate = ((body.get("inputRequests") or {}).get("approval") or {}).get("node")
        if last == status and (node is None or gate == node):
            return body
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {status}/{node} on {task_id}; last={last}")


def events(client, task_id, after=-1):
    return client.get(f"{BASE}/tasks/{task_id}/events", params={"after": after}).json()


def names(payload):
    return [e["event"].get("name") for e in payload["events"] if e["event"]["type"] == "CUSTOM"]


def start(client, key=KEY, goal=GOAL):
    r = client.post(f"{BASE}/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": goal}, "idempotency_key": key})
    assert r.status_code == 200, r.text
    return r.json()


def restart_core(client, task_id):
    """Stop the runner the way an event-loop shutdown does (no cancel reason → the run stays open)."""
    runner = runner_mod.get_runner(task_id)
    assert runner is not None and runner._task is not None

    async def stop():
        runner._task.cancel()
        await asyncio.gather(runner._task, return_exceptions=True)

    client.portal.call(stop)
    assert runner_mod.get_runner(task_id) is None  # the old process is gone


def test_a_crew_run_survives_a_core_restart_replays_exactly_and_finishes(client, db, real_runner, slot_gate):
    _as()
    task_id = start(client)["taskId"]
    parked = wait_for(client, task_id, "input_required", "approve")
    plan_hash = parked["inputRequests"]["approval"]["plan_hash"]
    before = events(client, task_id)
    assert "hypercode.approval.required" in names(before)
    assert before["calmCard"]["status"] == "waiting_on_you"

    restart_core(client, task_id)
    counts = client.portal.call(recovery_mod.recover_runs)
    assert counts["resume"] == 1 and counts["fail"] == 0

    again = wait_for(client, task_id, "input_required", "approve")
    assert again["inputRequests"]["approval"]["plan_hash"] == plan_hash  # same plan, not a new one
    after = events(client, task_id)
    assert after["events"][: len(before["events"])] == before["events"]  # replay is exact across the restart
    assert after["nextAfter"] == before["nextAfter"]

    # a retried start after the restart finds the same task instead of starting a second crew
    dup = start(client)
    assert dup["taskId"] == task_id and dup["deduplicated"] is True

    url = f"{BASE}/tasks/{task_id}/input"
    assert client.post(url, json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64}).status_code == 409
    assert client.post(url, json={"decision": "approve"}).status_code == 422
    assert client.post(url, json={"decision": "approve", "plan_hash": plan_hash}).status_code == 200

    done = wait_for(client, task_id, "completed")
    assert done["result"]["success"] is True
    final = events(client, task_id, after=before["nextAfter"])
    assert [e["seq"] for e in final["events"]] == list(range(before["nextAfter"] + 1, final["nextAfter"] + 1))
    assert final["events"][-1]["event"]["type"] == "RUN_FINISHED"
    assert {"hypercode.approval.resolved", "hypercode.plan.sealed", "hypercode.guard.verdict"} <= set(names(final))
    verdict = next(e["event"]["value"] for e in final["events"] if e["event"].get("name") == "hypercode.guard.verdict")
    assert verdict["verdict"] == "ALLOW" and verdict["bundleHash"].startswith("sha256:")
    assert final["calmCard"]["status"] == "done" and final["done"] is True and final["pollInterval"] is None
    assert db.query(GovernanceLedger).filter_by(action="crew_plan_approved").count() == 1
    assert slot_gate.active == 0


def test_cancelling_at_the_gate_stops_the_run_and_nothing_can_approve_it_after(client, db, real_runner):
    _as()
    task_id = start(client, key="cancel-at-gate-0001")["taskId"]
    parked = wait_for(client, task_id, "input_required", "approve")
    plan_hash = parked["inputRequests"]["approval"]["plan_hash"]

    r = client.post(f"{BASE}/tasks/{task_id}/cancel", json={"reason": "changed my mind"})
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    wait_for(client, task_id, "cancelled")
    ev = events(client, task_id)
    assert ev["events"][-1]["event"] == {"type": "RUN_ERROR", "message": "changed my mind (by bro)", "code": "CANCELLED"}
    assert ev["calmCard"]["status"] == "paused" and ev["done"] is True
    late = client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": plan_hash})
    assert late.status_code == 409
    assert db.query(GovernanceLedger).count() == 0


def test_after_a_restart_an_unreachable_orchestrator_fails_closed_with_no_mocked_green(
    client, db, real_runner, slot_gate, monkeypatch
):
    _as()
    task_id = start(client, key="restart-then-fail-0001")["taskId"]
    plan_hash = wait_for(client, task_id, "input_required", "approve")["inputRequests"]["approval"]["plan_hash"]
    restart_core(client, task_id)
    client.portal.call(recovery_mod.recover_runs)
    wait_for(client, task_id, "input_required", "approve")

    err = crew_dispatch.DispatchError("orchestrator unreachable (ConnectError)")
    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", _fake_dispatch(error=err))
    assert client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": plan_hash}).status_code == 200

    failed = wait_for(client, task_id, "failed")
    assert "unreachable" in failed["error"]
    ev = events(client, task_id)
    assert ev["events"][-1]["event"]["type"] == "RUN_ERROR" and ev["events"][-1]["event"]["code"] == "RUN_FAILED"
    assert "hypercode.guard.verdict" not in names(ev)  # no verdict from a stage that never ran
    assert ev["calmCard"]["status"] == "blocked"
    assert slot_gate.active == 0


def test_a_run_interrupted_in_the_middle_of_a_proposal_is_resumed_not_lost(client, db, real_runner, slot_gate, monkeypatch):
    """build is idempotent (propose-only), so a restart while it is in flight re-runs it safely."""
    _as()
    started = {"n": 0}
    release = {"go": False}

    async def slow_dispatch(**kw):
        started["n"] += 1
        while not release["go"]:
            await asyncio.sleep(0.02)
        return await _fake_dispatch()(**kw)

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", slow_dispatch)
    task_id = start(client, key="mid-proposal-0001")["taskId"]
    plan_hash = wait_for(client, task_id, "input_required", "approve")["inputRequests"]["approval"]["plan_hash"]
    client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": plan_hash})
    end = time.time() + 10
    while started["n"] == 0 and time.time() < end:
        time.sleep(0.02)
    assert started["n"] == 1  # the builder is mid-flight

    restart_core(client, task_id)
    assert slot_gate.active == 0  # cancellation released the slot
    counts = client.portal.call(recovery_mod.recover_runs)
    assert counts["resume"] == 1, counts  # build is idempotent → resumed

    release["go"] = True
    done = wait_for(client, task_id, "completed", timeout=20)
    assert done["result"]["success"] is True
    assert started["n"] >= 2  # the proposal was re-requested after the restart
    assert events(client, task_id)["calmCard"]["status"] == "done"
    assert slot_gate.active == 0
