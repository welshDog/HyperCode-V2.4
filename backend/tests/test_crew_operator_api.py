"""HyperCrew Day 2 — operator API: goal arguments, idempotency key, and the plan gate end to end."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agents.hyperflow.registry import get_flow
from app.api.v1.endpoints import operator_tasks
from app.crew import dispatch as crew_dispatch
from app.crew.evidence import sha256_hex
from app.main import app
from app.models.governance import GovernanceLedger
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

BASE = "/api/v1/operator"
GOAL = "add a health endpoint"
KEY = "bro-crew-key-0001"


def _as(kind="user", name="bro", user_id=1, is_superuser=True):
    app.dependency_overrides[operator_tasks.operator_principal] = lambda: {
        "kind": kind, "name": name, "user_id": user_id if kind == "user" else None,
        "is_superuser": is_superuser if kind == "user" else False,
    }


@pytest.fixture
def started(monkeypatch):
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(operator_tasks, "start_flow_run", mock)
    return mock


def _start(client, goal=GOAL, key=None, tool="hypercode.crew", arguments=None):
    body = {"tool": tool, "arguments": {"goal": goal} if arguments is None else arguments}
    if key is not None:
        body["idempotency_key"] = key
    return client.post(f"{BASE}/tasks", json=body)


# ── arguments ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("arguments", [{}, {"goal": ""}, {"goal": "hi"}, {"goal": 5}, {"goal": GOAL, "x": 1}])
def test_crew_rejects_bad_arguments(client, started, arguments):
    _as()
    assert _start(client, arguments=arguments).status_code == 422
    started.assert_not_awaited()


def test_error_does_not_echo_the_input(client, started):
    _as()
    r = _start(client, arguments={"goal": GOAL, "SUPERSECRET": "v"})
    assert r.status_code == 422 and "SUPERSECRET" not in r.text


def test_other_tools_still_reject_arguments(client, started):
    _as()
    assert _start(client, tool="hypercode.inspect", arguments={"goal": GOAL}).status_code == 422
    started.assert_not_awaited()


def test_crew_start_stores_cleaned_goal_before_the_flow_runs(client, db, started):
    _as()
    r = _start(client, goal="  add   a health\nendpoint password=hunter2 ")
    assert r.status_code == 200
    body = r.json()
    assert body["tool"] == "hypercode.crew" and body["status"] == "working" and "deduplicated" not in body
    assert started.await_args.args[0].name == "hypercode-crew"
    assert started.await_args.args[1] == body["taskId"]
    db.expire_all()
    run = db.get(HyperFlowRun, body["taskId"])
    stored = run.state["context"]["arguments"]["goal"]
    assert stored == "add a health endpoint password=***" and "hunter2" not in stored
    assert run.state["context"]["arguments_hash"].startswith("sha256:")
    assert run.status == "running" and run.current_node == "plan"


# ── idempotency ────────────────────────────────────────────────────────────────
def test_same_key_returns_the_same_task_and_starts_once(client, started):
    _as()
    first, second = _start(client, key=KEY).json(), _start(client, key=KEY).json()
    assert first["taskId"] == second["taskId"]
    assert second["deduplicated"] is True and "deduplicated" not in first
    assert started.await_count == 1


def test_same_key_different_goal_is_a_conflict(client, started):
    _as()
    assert _start(client, key=KEY).status_code == 200
    r = _start(client, goal="a completely different goal", key=KEY)
    assert r.status_code == 409 and r.json()["detail"]["error"] == "idempotency_key_reused"
    assert started.await_count == 1


def test_goal_whitespace_differences_are_the_same_request(client, started):
    _as()
    a = _start(client, goal="add a health endpoint", key=KEY).json()
    b = _start(client, goal="  add  a health\nendpoint ", key=KEY).json()
    assert a["taskId"] == b["taskId"] and b["deduplicated"] is True


def test_different_callers_never_share_a_key(client, started):
    _as(user_id=1)
    a = _start(client, key=KEY).json()
    _as(user_id=2)
    b = _start(client, key=KEY).json()
    _as(kind="agent", name="hypercode-mcp-server")
    c = _start(client, key=KEY).json()
    assert len({a["taskId"], b["taskId"], c["taskId"]}) == 3
    assert started.await_count == 3


def test_different_tools_never_share_a_key(client, started):
    _as()
    a = _start(client, key=KEY).json()
    b = _start(client, tool="hypercode.inspect", arguments={}, key=KEY).json()
    assert a["taskId"] != b["taskId"]


def test_key_works_for_tools_without_arguments(client, started):
    _as()
    a = _start(client, tool="hypercode.inspect", arguments={}, key=KEY).json()
    b = _start(client, tool="hypercode.inspect", arguments={}, key=KEY).json()
    assert a["taskId"] == b["taskId"] and b["deduplicated"] is True and started.await_count == 1


def test_no_key_means_a_new_task_each_time(client, started):
    _as()
    assert _start(client).json()["taskId"] != _start(client).json()["taskId"]


@pytest.mark.parametrize("key", ["short", "x" * 129, "has space here", "semi;colon-key", "", 123])
def test_bad_key_is_422(client, started, key):
    _as()
    assert _start(client, key=key).status_code == 422
    started.assert_not_awaited()


def test_duplicate_reports_the_current_status(client, db, started):
    _as()
    first = _start(client, key=KEY).json()
    db.expire_all()
    run = db.get(HyperFlowRun, first["taskId"])
    run.status = HyperFlowRunStatus.AWAITING_APPROVAL.value
    db.commit()
    again = _start(client, key=KEY).json()
    assert again["status"] == "input_required" and again["deduplicated"] is True
    assert again["pollInterval"] == 5000


def test_a_failed_start_marks_the_run_failed_and_surfaces_the_error(client, db, monkeypatch):
    _as()
    monkeypatch.setattr(operator_tasks, "start_flow_run", AsyncMock(side_effect=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        _start(client, key=KEY)
    db.expire_all()
    run = db.query(HyperFlowRun).one()
    assert run.status == "failed" and run.state["error"] == "could not start"


def test_plain_start_without_arguments_or_key_creates_no_row_up_front(client, db, started):
    _as()
    r = client.post(f"{BASE}/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    assert r.status_code == 200 and db.query(HyperFlowRun).count() == 0


# ── the plan gate over the API ─────────────────────────────────────────────────
def _seed_gate(db, run_id="crew-run-1"):
    from app.crew.plan import build_crew_plan, crew_plan_hash

    plan = build_crew_plan(GOAL, run_id)
    h = crew_plan_hash(plan)
    hist = [
        {"node": "plan", "type": "tool", "status": "completed",
         "result": {"success": True, "data": {"proposal": {"plan": plan, "plan_hash": h}}}},
        {"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval",
         "result": {"prompt": "Approve?", "plan_hash": h, "context": {"proposal": {"plan": plan, "plan_hash": h}}}},
    ]
    db.add(HyperFlowRun(id=run_id, flow_name="hypercode-crew", flow_version=1,
                        status="awaiting_approval", current_node="approve", state={"history": hist}))
    db.commit()
    return h


def test_get_shows_the_plan_and_its_hash_to_the_approver(client, db):
    _as()
    h = _seed_gate(db)
    body = client.get(f"{BASE}/tasks/crew-run-1").json()
    assert body["tool"] == "hypercode.crew" and body["status"] == "input_required"
    approval = body["inputRequests"]["approval"]
    assert approval["plan_hash"] == h and approval["node"] == "approve"
    assert approval["context"]["proposal"]["plan"]["goal"] == GOAL


def test_approve_needs_the_exact_plan_hash(client, db, monkeypatch):
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    _as()
    h = _seed_gate(db)
    url = f"{BASE}/tasks/crew-run-1/input"
    r = client.post(url, json={"decision": "approve"})
    assert r.status_code == 422 and r.json()["detail"]["error"] == "plan_hash_required"
    r = client.post(url, json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64})
    assert r.status_code == 409 and r.json()["detail"]["error"] == "plan_hash_mismatch"
    r = client.post(url, json={"decision": "approve", "plan_hash": h})
    assert r.status_code == 200 and r.json()["accepted"] is True


def test_an_agent_can_never_approve_a_crew_plan(client, db):
    _as(kind="agent", name="hypercode-mcp-server")
    h = _seed_gate(db)
    r = client.post(f"{BASE}/tasks/crew-run-1/input", json={"decision": "approve", "plan_hash": h})
    assert r.status_code == 403


def test_a_non_superuser_cannot_approve(client, db):
    _as(is_superuser=False)
    h = _seed_gate(db)
    r = client.post(f"{BASE}/tasks/crew-run-1/input", json={"decision": "approve", "plan_hash": h})
    assert r.status_code == 403


# ── the real runner, real flow, real tools ─────────────────────────────────────
GOOD_BUILD = "```diff\n+def health():\n+    return {'ok': True}\n```"


def _fake_dispatch(build=GOOD_BUILD, verify="Fine.\nVERDICT: PASS", error=None, calls=None):
    async def fake(**kw):
        if calls is not None:
            calls.append(kw)
        if error is not None:
            raise error
        text = build if kw["stage"] == "build" else verify
        return {"ok": True, "agent": kw["agent"], "role": kw["role"], "stage": kw["stage"],
                "status": "completed", "summary": text, "summary_hash": sha256_hex(text), "truncated": False}
    return fake


def _drive(monkeypatch, arguments, *, approve, shown_hash_override=None, dispatch=None, scribe="approve",
           shepherd="off"):
    """Run the whole crew flow. ``scribe`` answers the handover gate: approve | skip | wrong_hash.

    ``shepherd`` is SAFETY_SHEPHERD_MODE for the run: "off" by default (no Shepherd in the sandbox), or
    "monitor"/"enforce" with nothing listening, to prove the crew fails CLOSED when Safety Shepherd is down."""
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", shepherd)
    from tests.test_hyperflow import _runner_with_io

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", dispatch or _fake_dispatch())
    runner, final = _runner_with_io(get_flow("hypercode-crew"), "e2e-crew", monkeypatch)
    monkeypatch.setattr(runner, "_load_arguments_sync", lambda: arguments)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        for _ in range(150):
            if runner.parked_gate == "approve" or runner._task.done():
                break
            await asyncio.sleep(0.02)
        if runner.parked_gate == "approve":
            awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
            sent = shown_hash_override or awaiting["result"]["plan_hash"]

            def take(node_id=None):
                if node_id == "approve_scribe":  # the handover gate has its own draft hash
                    shown = [e for e in runner._history if e["node"] == "approve_scribe" and e["status"] == "awaiting_approval"][-1]
                    bad = "sha256:" + "0" * 64
                    runner._last_decision_meta = {
                        "by": "bro@example.com", "plan_hash": bad if scribe == "wrong_hash" else shown["result"]["plan_hash"]}
                    return scribe != "skip"
                runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": sent}
                return approve

            monkeypatch.setattr(runner, "_take_persisted_decision", take)
            runner.resume(approve)
        await runner._task

    asyncio.run(scenario())
    return runner, final


def _data(runner, node):
    return [e for e in runner._history if e["node"] == node and e["status"] == "completed"][0]["result"]["data"]


def test_e2e_approved_plan_runs_build_verify_and_guard_allows(monkeypatch, ledger_db, slot_gate):
    calls = []
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(calls=calls))
    assert final["status"] is HyperFlowRunStatus.COMPLETED, final.get("error")
    sealed = _data(runner, "seal")
    assert sealed["sealed"] and sealed["performed"] is False and sealed["approved_by"] == "bro@example.com"
    assert ledger_db().query(GovernanceLedger).filter_by(action="crew_plan_approved").count() == 1
    assert [c["stage"] for c in calls] == ["build", "verify"]
    assert [c["agent"] for c in calls] == ["coder-agent", "qa-engineer"]
    assert "PROPOSING only" in calls[0]["task"] and GOOD_BUILD in calls[1]["task"]
    guard = _data(runner, "guard")
    assert guard["allowed"] is True and guard["verdict"] == "ALLOW" and guard["performed"] is False
    assert [e["kind"] for e in guard["evidence_bundle"]["evidence"]] == ["diff", "log"]
    assert slot_gate.active == 0  # every slot handed back


def test_e2e_dispatch_nodes_report_slot_wait_and_ram(monkeypatch, ledger_db, slot_gate):
    runner, _ = _drive(monkeypatch, {"goal": GOAL}, approve=True)
    # the fake bypasses the slot wrapper's own fields; the runner adds them
    assert "slot_wait_ms" in _data(runner, "build") and "ram_available_mb" in _data(runner, "verify")


def test_e2e_a_failing_verdict_completes_with_a_block_not_a_crash(monkeypatch, ledger_db, slot_gate):
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True,
                           dispatch=_fake_dispatch(verify="Broken.\nVERDICT: FAIL"))
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    guard = _data(runner, "guard")
    assert guard["verdict"] == "BLOCK" and guard["failed_checks"] == ["verifier_verdict"]


def test_e2e_a_dangerous_proposal_is_blocked_by_the_guard(monkeypatch, ledger_db, slot_gate):
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True,
                           dispatch=_fake_dispatch(build="```sh\ngit push --force origin main\n```"))
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    assert _data(runner, "guard")["verdict"] == "BLOCK"


def test_e2e_an_unreachable_orchestrator_fails_the_run_and_never_mocks_green(monkeypatch, ledger_db, slot_gate):
    err = crew_dispatch.DispatchError("orchestrator unreachable (ConnectError)")
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(error=err))
    assert final["status"] is HyperFlowRunStatus.FAILED and "unreachable" in final["error"]
    assert not [e for e in runner._history if e["node"] in ("verify", "guard") and e["status"] == "completed"]
    assert slot_gate.active == 0


def test_e2e_a_blocked_dispatch_fails_the_run(monkeypatch, ledger_db, slot_gate):
    err = crew_dispatch.DispatchError("orchestrator status 'blocked', not completed")
    _, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(error=err))
    assert final["status"] is HyperFlowRunStatus.FAILED and "blocked" in final["error"]


def test_e2e_no_free_slot_fails_the_run_instead_of_starting_a_fourth_agent(monkeypatch, ledger_db, slot_gate):
    import app.agents.hyperflow_runner as runner_mod

    slot_gate._active = slot_gate.cap  # three agents already awake
    monkeypatch.setattr(runner_mod, "slot_timeout_s", lambda: 0.05)
    calls = []
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=True, dispatch=_fake_dispatch(calls=calls))
    assert final["status"] is HyperFlowRunStatus.FAILED and "no crew slot" in final["error"]
    assert calls == []  # nothing was dispatched
    assert slot_gate.active == slot_gate.cap  # we did not steal or leak a slot


def test_e2e_rejected_plan_fails_and_dispatches_nothing(monkeypatch, ledger_db, slot_gate):
    calls = []
    runner, final = _drive(monkeypatch, {"goal": GOAL}, approve=False, dispatch=_fake_dispatch(calls=calls))
    assert final["status"] is HyperFlowRunStatus.FAILED and "approval rejected" in final["error"]
    assert not [e for e in runner._history if e["node"] == "seal"] and calls == []
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_e2e_a_hash_for_a_different_plan_cannot_seal_or_dispatch(monkeypatch, ledger_db, slot_gate):
    calls = []
    _, final = _drive(monkeypatch, {"goal": GOAL}, approve=True,
                      shown_hash_override="sha256:" + "f" * 64, dispatch=_fake_dispatch(calls=calls))
    assert final["status"] is HyperFlowRunStatus.FAILED and calls == []
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_e2e_no_goal_never_reaches_the_gate_or_any_agent(monkeypatch, ledger_db, slot_gate):
    calls = []
    runner, final = _drive(monkeypatch, {}, approve=True, dispatch=_fake_dispatch(calls=calls))
    assert runner.parked_gate is None and calls == []
    assert not [e for e in runner._history if e["status"] == "awaiting_approval"]
    assert not [e for e in runner._history if e["node"] == "seal"]
    assert ledger_db().query(GovernanceLedger).count() == 0


def test_dispatch_node_without_a_sealed_plan_fails_closed(monkeypatch, slot_gate):
    from app.agents.hyperflow.schema import FlowDefinition
    from tests.test_hyperflow import _runner_with_io

    flow = FlowDefinition.model_validate({
        "name": "t", "entry": "build",
        "nodes": [{"id": "build", "type": "agent_dispatch", "agent": "coder-agent",
                   "params": {"stage": "build", "role": "builder"}}]})
    calls = []
    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", _fake_dispatch(calls=calls))
    runner, final = _runner_with_io(flow, "no-seal", monkeypatch)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED and "sealed plan" in final["error"] and calls == []
