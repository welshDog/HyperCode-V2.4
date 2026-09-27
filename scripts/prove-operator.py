"""Live proof for the BROski operator. Runs INSIDE hypercode-core so tokens never leave it:

    docker exec -i hypercode-core python - phase0 < scripts/prove-operator.py
    docker exec -i hypercode-core python - phase1 < scripts/prove-operator.py
    docker restart hypercode-core        # (after phase1 prints PARKED_TASK=<id>)
    docker exec -i hypercode-core python - phase2 <id> < scripts/prove-operator.py

phase0: auth boundary (401/403/404/409), stale-decision safety, legacy-route regression guards.
phase1: inspect -> completed report; cancel proof; then parks a two-gate task at input_required.
phase2: (after the restart) the parked task resumes at its gate, is approved twice, completes.
Prints only ids and PASS/FAIL lines. Never prints the token.
"""

import sys
import time
import uuid
from datetime import datetime, timezone

import httpx

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.hyperflow import HyperFlowRun
from app.models.models import User

ROOT = "http://localhost:8000"
BASE = ROOT + "/api/v1/operator"


def _token() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).first()
        if user is None:
            sys.exit("FAIL: no active superuser to mint a proof token for")
        return create_access_token(subject=user.id)
    finally:
        db.close()


HEADERS = {"Authorization": f"Bearer {_token()}"}


def call(method: str, path: str, **kw):
    r = httpx.request(method, BASE + path, headers=HEADERS, timeout=30, **kw)
    return r.status_code, r.json()


def wait_for(task_id: str, want: set, timeout: int = 120) -> dict:
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task_id}")
            last = body.get("status")
            if code == 200 and last in want:
                return body
        except httpx.HTTPError:
            pass  # core may still be restarting
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for {sorted(want)} on {task_id}; last status={last}")


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        sys.exit(1)


def _nonsuper_token():
    """Bearer token for an ACTIVE non-superuser, or None if there is none."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.is_superuser.is_(False), User.is_active.is_(True)).first()
        return None if user is None else create_access_token(subject=user.id)
    finally:
        db.close()


def _raw(method: str, url: str, headers=None, **kw):
    """Request with explicit headers (default: none at all). Returns (status, json-or-None)."""
    r = httpx.request(method, url, headers=headers or {}, timeout=30, **kw)
    try:
        body = r.json()
    except ValueError:
        body = None
    return r.status_code, body


def _detail_error(body):
    d = body.get("detail") if isinstance(body, dict) else None
    return d.get("error") if isinstance(d, dict) else None


def _cancel_quiet(task_id: str) -> None:
    """Best-effort cleanup; never raises and never masks the real error."""
    try:
        call("POST", f"/tasks/{task_id}/cancel", json={"reason": "phase0 proof cleanup"})
    except Exception:
        pass


def _start_smoke() -> str:
    code, h = call("POST", "/tasks", json={"tool": "hypercode.smoke", "arguments": {}})
    check(code == 200 and bool(h.get("taskId")), "hypercode.smoke started")
    return h["taskId"]


def _wait_gate(task_id: str, node: str, timeout: int = 120) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        try:
            code, b = call("GET", f"/tasks/{task_id}")
            gate = ((b.get("inputRequests") or {}).get("approval") or {}).get("node")
            if code == 200 and b.get("status") == "input_required" and gate == node:
                return b
        except httpx.HTTPError:
            pass
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for gate '{node}' on {task_id}")


def _row_context(task_id: str) -> dict:
    db = SessionLocal()
    try:
        run = db.get(HyperFlowRun, task_id)
        return dict((run.state or {}).get("context") or {}) if run is not None else {}
    finally:
        db.close()


def phase0() -> None:
    # 1. No credential -> 401
    code, _ = _raw("GET", f"{BASE}/tasks/{uuid.uuid4()}")
    check(code == 401, "unauthenticated GET /operator/tasks/<id> -> 401")
    code, _ = _raw("POST", f"{BASE}/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    check(code == 401, "unauthenticated POST /operator/tasks -> 401")

    # 2. Unknown tool -> 404 unknown_tool; non-empty arguments -> 422
    code, body = call("POST", "/tasks", json={"tool": "no.such.tool", "arguments": {}})
    check(code == 404 and _detail_error(body) == "unknown_tool", "unknown tool -> 404 unknown_tool")
    code, _ = call("POST", "/tasks", json={"tool": "hypercode.inspect", "arguments": {"x": 1}})
    check(code == 422, "non-empty arguments -> 422")

    # 3. Non-superuser human cannot approve
    ns_token = _nonsuper_token()
    if ns_token is None:
        print("SKIP: no active non-superuser user to test the 403")
    else:
        tid = _start_smoke()
        try:
            wait_for(tid, {"input_required"})
            code, _ = _raw(
                "POST", f"{BASE}/tasks/{tid}/input",
                headers={"Authorization": f"Bearer {ns_token}"}, json={"decision": "approve"},
            )
            check(code == 403, "non-superuser approve -> 403")
            time.sleep(3)
            _, after = call("GET", f"/tasks/{tid}")
            check(after["status"] == "input_required", "task still input_required after the rejected approval")
            code, cancelled = call("POST", f"/tasks/{tid}/cancel", json={"reason": "phase0 cleanup"})
            check(code == 200 and cancelled["status"] == "cancelled", "non-superuser test task cancelled")
        finally:
            _cancel_quiet(tid)

    # 4. Non-catalog flow is invisible to /operator
    rid = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(HyperFlowRun(
            id=rid, flow_name="implement-new-agent", flow_version=1,
            status="completed", state={"history": []},
        ))
        db.commit()
        code, _ = call("GET", f"/tasks/{rid}")
        check(code == 404, "non-catalog run: GET /operator/tasks/<id> -> 404")
        code, _ = call("POST", f"/tasks/{rid}/cancel", json={})
        check(code == 404, "non-catalog run: cancel via /operator -> 404")
    finally:
        try:
            db.rollback()
            row = db.get(HyperFlowRun, rid)
            if row is not None:
                db.delete(row)
                db.commit()
        except Exception:
            print(f"INFO: could not delete proof row {rid}; remove it manually")
        finally:
            db.close()

    # 5. Legacy resume route refuses operator runs
    tid = _start_smoke()
    try:
        wait_for(tid, {"input_required"})
        code, body = _raw(
            "POST", f"{ROOT}/api/v1/flows/runs/{tid}/resume", headers=HEADERS, json={"approved": True}
        )
        check(code == 409 and _detail_error(body) == "use_operator_api", "legacy /flows resume -> 409 use_operator_api")
        time.sleep(2)
        _, after = call("GET", f"/tasks/{tid}")
        check(after["status"] == "input_required", "task still input_required after legacy resume attempt")
        code, cancelled = call("POST", f"/tasks/{tid}/cancel", json={"reason": "phase0 cleanup"})
        check(code == 200 and cancelled["status"] == "cancelled", "legacy-resume test task cancelled")
    finally:
        _cancel_quiet(tid)

    # 6. A stale decision cannot approve the next gate
    tid = _start_smoke()
    try:
        _wait_gate(tid, "ready")
        code, body = call("POST", f"/tasks/{tid}/input", json={"decision": "approve"})
        check(code == 200 and body.get("accepted") is True, "gate 'ready' approved")
        _wait_gate(tid, "finish")
        print("INFO: parked at gate 'finish'; injecting a stale decision scoped to 'ready'")
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, tid, with_for_update=True)
            check(run is not None, "run row present for stale-decision injection")
            state = dict(run.state or {})
            ctx = dict(state.get("context") or {})
            ctx["pending_decision"] = {
                "approved": True, "by": "proof",
                "ts": datetime.now(timezone.utc).isoformat(), "node": "ready",
            }
            state["context"] = ctx
            run.state = state
            db.commit()
        finally:
            db.close()
        time.sleep(8)  # the runner polls about every 2 s
        _, after = call("GET", f"/tasks/{tid}")
        gate = ((after.get("inputRequests") or {}).get("approval") or {}).get("node")
        check(
            after["status"] == "input_required" and gate == "finish",
            "stale decision did NOT approve gate 'finish' (still input_required)",
        )
        check(
            "pending_decision" not in _row_context(tid),
            "runner discarded the stale decision (pending_decision gone from row)",
        )
        code, cancelled = call("POST", f"/tasks/{tid}/cancel", json={"reason": "phase0 cleanup"})
        check(code == 200 and cancelled["status"] == "cancelled", "stale-decision test task cancelled")
    finally:
        _cancel_quiet(tid)

    # 7. Regression
    code, _ = _raw("GET", f"{ROOT}/health")
    check(code == 200, "core GET /health -> 200")
    code, flows = _raw("GET", f"{ROOT}/api/v1/flows")
    names = {f.get("name") for f in flows} if code == 200 and isinstance(flows, list) else set()
    check(
        code == 200 and {"operator-inspect", "hyperflow-smoke"} <= names,
        "GET /api/v1/flows lists operator-inspect + hyperflow-smoke",
    )
    code, h = call("POST", "/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    check(code == 200 and bool(h.get("taskId")), "inspect started")
    done = wait_for(h["taskId"], {"completed", "failed"})
    check(done["status"] == "completed", "inspect completed")
    code, legacy = _raw("GET", f"{ROOT}/api/v1/flows/runs/{h['taskId']}")  # deliberately NO Authorization header
    check(code == 200 and isinstance(legacy, dict), "legacy GET /flows/runs/<id> (unauthenticated) -> 200")
    leaked = [
        e for e in legacy.get("history", [])
        if isinstance(e, dict) and isinstance(e.get("result"), dict) and "data" in e["result"]
    ]
    check(not leaked, "legacy run endpoint history has no result.data (inspect report not leaked)")
    report = (done.get("result") or {}).get("report")
    check(isinstance(report, dict) and "ok" in report, "operator GET still returns result.report with 'ok'")
    print("PASS: phase0 complete")


def phase1() -> None:
    code, h = call("POST", "/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    check(code == 200 and h["status"] == "working" and h["taskId"], "inspect returns a handle immediately")
    done = wait_for(h["taskId"], {"completed", "failed"})
    check(done["status"] == "completed", "inspect completed after we 'disconnected' and polled later")
    report = done["result"]["report"]
    print(f"INFO: stack ok={report['ok']} attention={report['attention']}")
    check(all(k in report for k in ("containers", "redis", "postgres", "queues", "disk")), "report has all sections")

    code, c = call("POST", "/tasks", json={"tool": "hypercode.smoke", "arguments": {}})
    wait_for(c["taskId"], {"input_required"})
    code, cancelled = call("POST", f"/tasks/{c['taskId']}/cancel", json={"reason": "proof cancel"})
    check(code == 200 and cancelled["status"] == "cancelled", "cancel mid-flight -> cancelled")
    time.sleep(3)
    _, after = call("GET", f"/tasks/{c['taskId']}")
    check(after["status"] == "cancelled", "cancelled task stays cancelled (no further transitions)")

    code, p = call("POST", "/tasks", json={"tool": "hypercode.smoke", "arguments": {}})
    parked = wait_for(p["taskId"], {"input_required"})
    check(parked["inputRequests"]["approval"]["question"], "run parked at an approval gate")
    print(f"PARKED_TASK={p['taskId']}")


def phase2(task_id: str) -> None:
    wait_for(task_id, {"input_required"})
    print("INFO: parked task is visible again after the restart")
    for gate in (1, 2):
        code, body = call("POST", f"/tasks/{task_id}/input", json={"decision": "approve"})
        check(code == 200 and body["accepted"], f"approval {gate} accepted after restart")
        if gate == 1:
            # Wait for the run to reach the SECOND gate (not the still-visible first one).
            end = time.time() + 120
            while time.time() < end:
                _, b = call("GET", f"/tasks/{task_id}")
                if b["status"] == "input_required" and (b.get("inputRequests") or {}).get("approval", {}).get("node") == "finish":
                    break
                time.sleep(2)
            else:
                sys.exit("FAIL: second gate never appeared")
    done = wait_for(task_id, {"completed", "failed"})
    check(done["status"] == "completed", "task completed after approvals that survived a core restart")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phase0":
        phase0()
    elif len(sys.argv) >= 2 and sys.argv[1] == "phase1":
        phase1()
    elif len(sys.argv) >= 3 and sys.argv[1] == "phase2":
        phase2(sys.argv[2])
    else:
        sys.exit("usage: phase0 | phase1 | phase2 <task_id>")
