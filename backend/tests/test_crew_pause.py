"""HyperCrew Day 6 — Panic / pause: the runner holds between steps, the hold is durable, and only a human resumes."""

import asyncio
import time

import pytest

import app.agents.hyperflow_runner as runner_mod
import app.broski_operator.recovery as recovery_mod
from app.agents.hyperflow.schema import FlowDefinition
from app.api.v1.endpoints import operator_tasks
from app.broski_operator.runs import clear_paused, pause_info, set_paused
from app.crew import dispatch as crew_dispatch
from app.crew.agui import history_to_events
from app.crew.cards import calm_card_for_run
from app.main import app
from app.models.governance import GovernanceLedger
from app.models.hyperflow import HyperFlowRun
from tests.test_crew_operator_api import GOAL, _as, _fake_dispatch
from tests.test_crew_restart_proof import events, restart_core, start, wait_for
from tests.test_hyperflow import _runner_with_io

BASE = "/api/v1/operator"


def two_step_flow():
    return FlowDefinition.model_validate({
        "name": "two-step", "entry": "a",
        "nodes": [{"id": "a", "type": "tool", "tool": "t.a"}, {"id": "b", "type": "tool", "tool": "t.b"}],
        "edges": [{"from": "a", "to": "b"}],
    })


# ── runner: pause holds between steps ─────────────────────────────────────────────
def test_a_paused_runner_starts_no_step_until_resumed(monkeypatch):
    runner, final = _runner_with_io(two_step_flow(), "p1", monkeypatch)
    ran = []

    async def dispatch(node):
        ran.append(node.id)
        return {"ok": True, "green": True}

    monkeypatch.setattr(runner, "_dispatch", dispatch)

    async def scenario():
        runner.request_pause()
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.15)
        assert ran == [] and not runner._task.done()  # held before the very first step
        assert [e["status"] for e in runner._history if e["type"] == "control"] == ["paused"]
        runner.request_resume()
        await runner._task

    asyncio.run(scenario())
    assert ran == ["a", "b"] and final["status"].value == "completed"
    assert [e["status"] for e in runner._history if e["type"] == "control"] == ["paused", "resumed"]


def test_a_step_in_flight_finishes_then_the_run_holds(monkeypatch):
    runner, final = _runner_with_io(two_step_flow(), "p2", monkeypatch)
    ran, release = [], {"go": False}

    async def dispatch(node):
        ran.append(node.id)
        while not release["go"]:
            await asyncio.sleep(0.01)
        return {"ok": True, "green": True}

    monkeypatch.setattr(runner, "_dispatch", dispatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.1)
        assert ran == ["a"]
        runner.request_pause()  # panic while step a is running
        release["go"] = True
        await asyncio.sleep(0.2)
        assert ran == ["a"]  # a finished, b was NOT started
        assert runner._history[-1]["status"] == "paused" and runner._history[-1]["result"] == {"next": "b"}
        runner.request_resume()
        await runner._task

    asyncio.run(scenario())
    assert ran == ["a", "b"]


def test_cancel_still_works_while_paused(monkeypatch):
    runner, final = _runner_with_io(two_step_flow(), "p3", monkeypatch)

    async def scenario():
        runner.request_pause()
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.1)
        assert await runner.cancel("stop (by bro)") is True

    asyncio.run(scenario())
    assert final["status"].value == "cancelled" and "stop" in final["error"]


def test_resume_without_a_pause_is_harmless(monkeypatch):
    runner, final = _runner_with_io(two_step_flow(), "p4", monkeypatch)
    runner.request_resume()
    monkeypatch.setattr(runner, "_dispatch", lambda node: _ok())
    asyncio.run(runner._run())
    assert final["status"].value == "completed" and not [e for e in runner._history if e["type"] == "control"]


async def _ok():
    return {"ok": True, "green": True}


# ── recovery: a hold is not a step ────────────────────────────────────────────────
def _hist(*entries):
    return [dict(zip(("node", "type", "status"), e), result={}) for e in entries]


def test_recovery_ignores_pause_markers_when_deciding_what_to_do():
    flow = two_step_flow()
    done_a = _hist(("a", "tool", "completed"), (None, "control", "paused"))
    assert recovery_mod.plan_recovery(flow, "running", done_a).action == "fail"  # b is not idempotent: same as without the marker
    idem = FlowDefinition.model_validate({
        "name": "t", "entry": "a",
        "nodes": [{"id": "a", "type": "tool", "tool": "t.a"}, {"id": "b", "type": "tool", "tool": "t.b", "idempotent": True}],
        "edges": [{"from": "a", "to": "b"}],
    })
    plan = recovery_mod.plan_recovery(idem, "running", _hist(("a", "tool", "completed"), (None, "control", "paused")))
    assert plan.action == "resume" and plan.node_id == "b"


def test_recovery_resumes_a_paused_run_that_was_parked_at_its_gate():
    flow = FlowDefinition.model_validate({
        "name": "g", "entry": "gate", "nodes": [{"id": "gate", "type": "human_approval_gate"}], "edges": []})
    plan = recovery_mod.plan_recovery(flow, "awaiting_approval", _hist(("gate", "human_approval_gate", "awaiting_approval"), (None, "control", "paused")))
    assert plan.action == "resume" and plan.node_id == "gate"


# ── events + card ───────────────────────────────────────────────────────────────
def test_pause_markers_become_events_and_stay_append_only():
    hist = [
        {"node": "a", "type": "tool", "status": "completed", "result": {"success": True}},
        {"node": None, "type": "control", "status": "paused", "result": {"next": "b"}},
        {"node": None, "type": "control", "status": "resumed", "result": {"next": "b"}},
    ]
    names = [e["event"].get("name") for e in history_to_events("r", hist) if e["event"]["type"] == "CUSTOM"]
    assert names == ["hypercode.run.paused", "hypercode.run.resumed"]
    prev = history_to_events("r", [])
    for k in range(1, len(hist) + 1):
        cur = history_to_events("r", hist[:k])
        assert cur[: len(prev)] == prev
        prev = cur


def card(**kw):
    base = dict(run_id="r", run_status="running", history=[], current_node="build", error=None, at_gate=False, paused=True)
    base.update(kw)
    return calm_card_for_run(**base)


def test_card_says_pausing_until_the_runner_has_actually_stopped():
    c = card()
    assert c.status == "paused" and c.next_action == "Resume when you are ready"
    assert c.tldr[-1] == "Pausing: the step in progress finishes first."


def test_card_says_nothing_is_running_once_it_has_stopped_or_is_at_the_gate():
    stopped = card(history=[{"node": None, "type": "control", "status": "paused", "result": {}}])
    assert stopped.tldr[-1] == "Paused. Nothing is running."
    assert card(run_status="awaiting_approval", at_gate=True).tldr[-1] == "Paused. Nothing is running."


def test_a_stale_pause_marker_does_not_claim_a_new_hold_has_settled():
    hist = [{"node": None, "type": "control", "status": "paused", "result": {}},
            {"node": None, "type": "control", "status": "resumed", "result": {}}]
    assert card(history=hist).tldr[-1] == "Pausing: the step in progress finishes first."


@pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
def test_a_pause_flag_never_changes_the_card_of_a_finished_run(status):
    assert card(run_status=status, paused=True) == card(run_status=status, paused=False)


# ── runs helpers ──────────────────────────────────────────────────────────────────
def test_set_and_clear_pause_keep_the_first_snapshot_and_the_rest_of_the_context(db):
    db.add(HyperFlowRun(id="h1", flow_name="hypercode-crew", flow_version=2, status="running",
                        state={"history": [], "context": {"arguments": {"goal": GOAL}}}))
    db.commit()
    run = db.get(HyperFlowRun, "h1")
    assert pause_info(run) is None
    assert set_paused(db, run, by="bro", reason="panic", snapshot={"n": 1}) is True
    assert set_paused(db, run, by="other", reason="again", snapshot={"n": 2}) is False
    info = pause_info(run)
    assert info["by"] == "bro" and info["snapshot"] == {"n": 1}
    assert run.state["context"]["arguments"] == {"goal": GOAL}  # untouched
    assert clear_paused(db, run)["snapshot"] == {"n": 1}
    assert pause_info(run) is None and clear_paused(db, run) is None
    assert run.state["context"]["arguments"] == {"goal": GOAL}


# ── API ───────────────────────────────────────────────────────────────────────────
def seed(db, run_id="r1", status="running", node="build", flow="hypercode-crew", history=None, context=None):
    state = {"history": history or []}
    if context:
        state["context"] = context
    db.add(HyperFlowRun(id=run_id, flow_name=flow, flow_version=2, status=status, current_node=node, state=state))
    db.commit()


def test_pause_stores_a_snapshot_and_a_second_pause_keeps_the_first(client, db):
    _as()
    seed(db, history=[{"node": "plan", "type": "tool", "status": "completed", "result": {"success": True}}])
    r = client.post(f"{BASE}/tasks/r1/pause", json={})
    assert r.status_code == 200 and r.json()["paused"] is True and r.json()["alreadyPaused"] is False
    snap = r.json()["snapshot"]
    assert snap["currentNode"] == "build" and snap["card"]["tldr"][0] == "Plan written"
    assert snap["card"]["next_action"] and len(snap["card"]["tldr"]) <= 5
    again = client.post(f"{BASE}/tasks/r1/pause", json={}).json()
    assert again["alreadyPaused"] is True and again["snapshot"] == snap
    db.expire_all()
    assert pause_info(db.get(HyperFlowRun, "r1"))["by"] == "bro"


def test_pause_refuses_finished_and_unknown_runs(client, db):
    _as()
    seed(db, run_id="done", status="completed", node=None)
    assert client.post(f"{BASE}/tasks/done/pause", json={}).status_code == 409
    assert client.post(f"{BASE}/tasks/nope/pause", json={}).status_code == 404
    seed(db, run_id="other", flow="not-a-catalog-flow")
    assert client.post(f"{BASE}/tasks/other/pause", json={}).status_code == 404
    assert client.post(f"{BASE}/tasks/done/pause", json={"reason": "x" * 500}).status_code == 422


def test_an_agent_can_pause_but_never_resume(client, db):
    seed(db)
    _as(kind="agent", name="hypercode-mcp-server")
    assert client.post(f"{BASE}/tasks/r1/pause", json={}).status_code == 200
    assert client.post(f"{BASE}/tasks/r1/resume").status_code == 403
    assert client.post(f"{BASE}/panic/resume").status_code == 403
    _as()
    r = client.post(f"{BASE}/tasks/r1/resume")
    assert r.status_code == 200 and r.json()["paused"] is False and r.json()["snapshot"]["card"]
    assert client.post(f"{BASE}/tasks/r1/resume").status_code == 409  # not paused any more


def test_a_paused_run_cannot_be_approved_until_resumed(client, db):
    _as()
    from tests.test_crew_operator_api import _seed_gate

    h = _seed_gate(db)
    assert client.post(f"{BASE}/tasks/crew-run-1/pause", json={}).status_code == 200
    r = client.post(f"{BASE}/tasks/crew-run-1/input", json={"decision": "approve", "plan_hash": h})
    assert r.status_code == 409 and r.json()["detail"] == {"error": "paused"}
    assert client.post(f"{BASE}/tasks/crew-run-1/resume").status_code == 200
    assert client.post(f"{BASE}/tasks/crew-run-1/input", json={"decision": "approve", "plan_hash": h}).status_code == 200


def test_task_and_events_report_the_pause_and_the_paused_card(client, db):
    _as()
    seed(db)
    client.post(f"{BASE}/tasks/r1/pause", json={})
    t = client.get(f"{BASE}/tasks/r1").json()
    assert t["paused"] is True and t["pausedAt"] and t["status"] == "working"
    ev = client.get(f"{BASE}/tasks/r1/events").json()
    assert ev["paused"] is True and ev["calmCard"]["status"] == "paused" and ev["now"] is None
    client.post(f"{BASE}/tasks/r1/resume")
    assert client.get(f"{BASE}/tasks/r1").json()["paused"] is False
    assert client.get(f"{BASE}/tasks/r1/events").json()["calmCard"]["status"] == "running"


def test_a_finished_run_never_reports_paused(client, db):
    _as()
    seed(db, status="completed", node=None, context={"paused": {"at": "t", "by": "x", "snapshot": {}}})
    assert client.get(f"{BASE}/tasks/r1").json()["paused"] is False
    assert client.get(f"{BASE}/tasks/r1/events").json()["paused"] is False


def test_panic_with_nothing_running_says_so(client, db, real_runner):
    _as()
    body = client.post(f"{BASE}/panic").json()
    assert body["saved"] is True and body["paused"] == [] and body["message"] == "Nothing was running. You are all clear."


def test_panic_pauses_every_open_operator_run_and_nothing_else(client, db, real_runner):
    _as()
    seed(db, run_id="mid", status="running", node="build")
    seed(db, run_id="gate", status="awaiting_approval", node="approve",
         history=[{"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}])
    seed(db, run_id="inspect", status="running", node="inspect", flow="operator-inspect")
    seed(db, run_id="done", status="completed", node=None)
    seed(db, run_id="foreign", status="running", node="x", flow="not-an-operator-flow")
    body = client.post(f"{BASE}/panic").json()
    assert {p["taskId"] for p in body["paused"]} == {"mid", "gate", "inspect"}
    # the snapshot is WHERE THE RUN WAS when you paused (not the paused card): it is what "where was I?" shows
    assert all(p["card"]["tldr"] and p["card"]["next_action"] for p in body["paused"])
    assert not any(p["card"]["status"] == "paused" for p in body["paused"])
    assert body["message"] == "Saved. The step in progress will finish, then nothing else will run."
    db.expire_all()
    assert pause_info(db.get(HyperFlowRun, "done")) is None and pause_info(db.get(HyperFlowRun, "foreign")) is None
    assert db.query(GovernanceLedger).filter_by(action="panic_used").count() == 1 and body["ledger"] is True


def test_panic_when_only_parked_at_a_gate_says_nothing_is_running(client, db, real_runner):
    _as()
    seed(db, run_id="gate", status="awaiting_approval", node="approve",
         history=[{"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}])
    assert client.post(f"{BASE}/panic").json()["message"] == "Saved. Nothing is running. Take your time."


def test_a_second_panic_changes_nothing_and_is_not_an_error(client, db, real_runner):
    _as()
    seed(db)
    first = client.post(f"{BASE}/panic").json()
    second = client.post(f"{BASE}/panic").json()
    assert [p["taskId"] for p in first["paused"]] == ["r1"] and second["paused"] == [] and second["alreadyPaused"] == ["r1"]
    assert second["saved"] is True


def test_panic_is_saved_even_if_the_ledger_is_down(client, db, real_runner, monkeypatch):
    _as()
    seed(db)

    def boom():
        raise RuntimeError("ledger down")

    monkeypatch.setattr("app.db.session.SessionLocal", boom)
    body = client.post(f"{BASE}/panic").json()
    assert body["saved"] is True and body["ledger"] is False and [p["taskId"] for p in body["paused"]] == ["r1"]
    db.expire_all()
    assert pause_info(db.get(HyperFlowRun, "r1")) is not None


def test_panic_status_survives_a_refresh_and_resume_all_releases_everything(client, db, real_runner):
    _as()
    seed(db, run_id="a")
    seed(db, run_id="b", status="awaiting_approval", node="approve",
         history=[{"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}])
    assert client.get(f"{BASE}/panic").json() == {"paused": []}
    client.post(f"{BASE}/panic")
    held = client.get(f"{BASE}/panic").json()["paused"]
    assert {h["taskId"] for h in held} == {"a", "b"} and all(h["pausedAt"] and h["card"] for h in held)
    assert set(client.post(f"{BASE}/panic/resume").json()["resumed"]) == {"a", "b"}
    assert client.get(f"{BASE}/panic").json() == {"paused": []}
    assert client.post(f"{BASE}/panic/resume").json() == {"resumed": []}


def test_panic_endpoints_need_authentication(client, db):
    app.dependency_overrides.pop(operator_tasks.operator_principal, None)
    for method, path in (("POST", "/panic"), ("GET", "/panic"), ("POST", "/panic/resume"), ("POST", "/tasks/x/pause")):
        assert client.request(method, f"{BASE}{path}", json={} if "pause" in path else None).status_code == 401


# ── the real runner, real recovery ──────────────────────────────────────────────────
def approve(client, task_id, plan_hash):
    return client.post(f"{BASE}/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": plan_hash})


def test_panic_at_the_gate_holds_through_a_core_restart_until_a_human_resumes(client, db, real_runner, slot_gate):
    _as()
    task_id = start(client, key="panic-gate-restart-1")["taskId"]
    plan_hash = wait_for(client, task_id, "input_required", "approve")["inputRequests"]["approval"]["plan_hash"]
    panic = client.post(f"{BASE}/panic").json()
    assert [p["taskId"] for p in panic["paused"]] == [task_id]
    assert approve(client, task_id, plan_hash).status_code == 409  # held

    restart_core(client, task_id)
    assert client.portal.call(recovery_mod.recover_runs)["resume"] == 1
    held = wait_for(client, task_id, "working")
    assert held["paused"] is True  # the hold survived the restart: the recovered runner waits BEFORE the gate
    assert events(client, task_id)["calmCard"]["tldr"][-1] == "Paused. Nothing is running."
    assert approve(client, task_id, plan_hash).status_code == 409

    assert client.post(f"{BASE}/tasks/{task_id}/resume").status_code == 200
    wait_for(client, task_id, "input_required", "approve")  # released: it parks at the gate again, same plan
    assert approve(client, task_id, plan_hash).status_code == 200
    assert wait_for(client, task_id, "completed")["result"]["success"] is True
    assert events(client, task_id)["calmCard"]["status"] == "done"


def test_panic_mid_run_lets_the_step_finish_then_holds_before_the_next_one(client, db, real_runner, slot_gate, monkeypatch):
    _as()
    release, calls = {"go": False}, []

    async def slow(**kw):
        calls.append(kw["stage"])
        while not release["go"] and kw["stage"] == "build":
            await asyncio.sleep(0.02)
        return await _fake_dispatch()(**kw)

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", slow)
    task_id = start(client, key="panic-mid-run-0001")["taskId"]
    plan_hash = wait_for(client, task_id, "input_required", "approve")["inputRequests"]["approval"]["plan_hash"]
    assert approve(client, task_id, plan_hash).status_code == 200
    end = time.time() + 10
    while calls != ["build"] and time.time() < end:
        time.sleep(0.02)
    assert calls == ["build"]

    panic = client.post(f"{BASE}/panic").json()
    assert panic["message"] == "Saved. The step in progress will finish, then nothing else will run."
    assert events(client, task_id)["calmCard"]["tldr"][-1] == "Pausing: the step in progress finishes first."

    release["go"] = True
    end = time.time() + 10
    ev = events(client, task_id)
    while ev["calmCard"]["tldr"][-1] != "Paused. Nothing is running." and time.time() < end:
        time.sleep(0.05)
        ev = events(client, task_id)
    assert ev["calmCard"]["tldr"][-1] == "Paused. Nothing is running."
    assert "hypercode.run.paused" in [e["event"].get("name") for e in ev["events"]]
    time.sleep(0.3)
    assert calls == ["build"]  # verify has NOT started while paused
    assert slot_gate.active == 0  # nothing is holding a slot while held

    client.post(f"{BASE}/panic/resume")
    done = wait_for(client, task_id, "completed")
    assert done["result"]["success"] is True and calls == ["build", "verify"]
    assert "hypercode.run.resumed" in [e["event"].get("name") for e in events(client, task_id)["events"]]


def test_a_pause_set_while_the_runner_is_down_is_honoured_after_recovery(client, db, real_runner, slot_gate, monkeypatch):
    """The in-memory flag is only a fast path: the durable record is what a recovered runner obeys."""
    _as()
    release, calls = {"go": False}, []

    async def slow(**kw):
        calls.append(kw["stage"])
        while not release["go"]:
            await asyncio.sleep(0.02)
        return await _fake_dispatch()(**kw)

    monkeypatch.setattr(crew_dispatch, "dispatch_to_agent", slow)
    task_id = start(client, key="panic-while-down-0001")["taskId"]
    plan_hash = wait_for(client, task_id, "input_required", "approve")["inputRequests"]["approval"]["plan_hash"]
    approve(client, task_id, plan_hash)
    end = time.time() + 10
    while not calls and time.time() < end:
        time.sleep(0.02)
    restart_core(client, task_id)  # the runner process is gone; the run row says "running"
    assert runner_mod.get_runner(task_id) is None
    assert client.post(f"{BASE}/panic").json()["paused"][0]["taskId"] == task_id  # no live runner to tell

    release["go"] = True
    assert client.portal.call(recovery_mod.recover_runs)["resume"] == 1
    time.sleep(0.4)
    assert wait_for(client, task_id, "working")["paused"] is True
    assert calls.count("verify") == 0  # the recovered runner stopped before doing anything new
    client.post(f"{BASE}/tasks/{task_id}/resume")
    assert wait_for(client, task_id, "completed")["result"]["success"] is True


def test_cancelling_a_paused_run_still_works(client, db, real_runner):
    _as()
    task_id = start(client, key="panic-cancel-0001")["taskId"]
    wait_for(client, task_id, "input_required", "approve")
    client.post(f"{BASE}/panic")
    assert client.post(f"{BASE}/tasks/{task_id}/cancel", json={"reason": "never mind"}).status_code == 200
    wait_for(client, task_id, "cancelled")
    ev = events(client, task_id)
    assert ev["paused"] is False and ev["calmCard"]["status"] == "paused" and ev["events"][-1]["event"]["code"] == "CANCELLED"
