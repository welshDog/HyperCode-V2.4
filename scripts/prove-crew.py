"""LIVE proof for HyperCrew. Runs INSIDE hypercode-core so tokens never leave it:

    docker exec -i hypercode-core python - phase0 < scripts/prove-crew.py
    docker exec -i hypercode-core python - phase1 < scripts/prove-crew.py     # prints PARKED_TASK / PARKED_KEY / PARKED_NEXT_AFTER
    docker restart hypercode-core                                              # (real container restart, run parked at the gate)
    docker exec -i hypercode-core python - phase2 <PARKED_TASK> <PARKED_KEY> <PARKED_NEXT_AFTER> < scripts/prove-crew.py

phase0: auth + validation + idempotency + approval-hash rules + events/Calm Card + cancel.
phase1: starts a crew run and parks it at the plan gate.
phase2: (after the restart) the run was resumed with the SAME plan and the SAME events, a retried start returns the
        same task, the exact plan hash is accepted, and the run ends either COMPLETED with a guard verdict (agents are
        up) or FAILED CLOSED (agents are down, no mocked green). Both are valid outcomes; each is checked.
Nothing here builds, writes or deploys anything: agents only propose text. Prints ids and PASS/FAIL lines only.
Not run in the session that wrote it (no Docker there) — the same path is proved locally by prove-crew-local.py.
"""

import os
import sys
import time
import uuid

import httpx

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

ROOT = os.getenv("PROVE_CORE_URL", "http://localhost:8000")  # override only to rehearse against a local harness
BASE = ROOT + "/api/v1/operator"
GOAL = "add a health endpoint to the API"


def _token(superuser: bool = True):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.is_superuser.is_(superuser), User.is_active.is_(True)).first()
        return None if user is None else create_access_token(subject=user.id)
    finally:
        db.close()


_TOKEN = _token(True)
if _TOKEN is None:
    sys.exit("FAIL: no active superuser to mint a proof token for")
HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def call(method: str, path: str, headers=None, **kw):
    r = httpx.request(method, BASE + path, headers=HEADERS if headers is None else headers, timeout=30, **kw)
    try:
        body = r.json()
    except ValueError:
        body = None
    return r.status_code, body


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        sys.exit(1)


def start(goal: str = GOAL, key: str | None = None, headers=None):
    body = {"tool": "hypercode.crew", "arguments": {"goal": goal}}
    if key is not None:
        body["idempotency_key"] = key
    return call("POST", "/tasks", headers=headers, json=body)


def events(task_id: str, after: int = -1):
    code, body = call("GET", f"/tasks/{task_id}/events", params={"after": after})
    check(code == 200, f"events endpoint answers for {task_id}")
    return body


def names(payload: dict) -> list:
    return [e["event"].get("name") for e in payload["events"] if e["event"]["type"] == "CUSTOM"]


def wait_for(task_id: str, want, timeout: int = 180) -> dict:
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task_id}")
            last = body.get("status") if body else None
            if code == 200 and want(body):
                return body
        except httpx.HTTPError:
            pass  # core may still be restarting
        time.sleep(2)
    sys.exit(f"FAIL: timed out on {task_id}; last status={last}")


def gate(body: dict) -> bool:
    return body["status"] == "input_required" and ((body.get("inputRequests") or {}).get("approval") or {}).get("node") == "approve"


def plan_hash_of(body: dict) -> str:
    return body["inputRequests"]["approval"]["plan_hash"]


def phase0() -> None:
    run = uuid.uuid4().hex[:8]
    check(start(headers={})[0] == 401, "unauthenticated start is refused (401)")
    check(call("GET", "/tasks/x/events", headers={})[0] == 401, "unauthenticated events are refused (401)")
    check(start(goal="hi")[0] == 422 and call("POST", "/tasks", json={"tool": "hypercode.crew", "arguments": {}})[0] == 422, "a missing or too-short goal is refused (422)")
    code, body = call("POST", "/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": GOAL, "SUPERSECRETFIELD": 1}})
    check(code == 422 and "SUPERSECRETFIELD" not in str(body), "an unexpected argument is refused without echoing it (422)")
    check(start(key="short")[0] == 422, "a bad idempotency key is refused (422)")
    check(call("POST", "/tasks", json={"tool": "hypercode.inspect", "arguments": {"goal": GOAL}})[0] == 422, "other tools still refuse arguments (422)")

    key = f"prove-crew-{run}-p0"
    code, h = start(key=key)
    check(code == 200 and h["status"] == "working", "crew started, handle returned at once")
    task_id = h["taskId"]
    code, dup = start(key=key)
    check(code == 200 and dup["taskId"] == task_id and dup.get("deduplicated") is True, "retrying with the same key returns the SAME task")
    check(start(goal="a completely different goal", key=key)[0] == 409, "same key + different goal is refused (409)")

    body = wait_for(task_id, gate)
    h = plan_hash_of(body)
    ev = events(task_id)
    check(ev["events"][0]["event"]["type"] == "RUN_STARTED" and [e["seq"] for e in ev["events"]] == list(range(len(ev["events"]))), "events start with RUN_STARTED, contiguous sequence")
    ask = str([e for e in ev["events"] if e["event"].get("name") == "hypercode.approval.required"])
    check("planHash" in ask and "stages" not in ask and GOAL not in ask, "approval event carries the plan hash, not the plan body")
    check(ev["calmCard"]["status"] == "waiting_on_you" and len(ev["calmCard"]["tldr"]) <= 5, "Calm Card: waiting on you, at most five lines")
    check(events(task_id, after=ev["nextAfter"])["events"] == [], "asking after the last sequence returns nothing new")
    check(call("POST", f"/tasks/{task_id}/input", json={"decision": "approve"})[0] == 422, "approve without the plan hash is refused (422)")
    check(call("POST", f"/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64})[0] == 409, "approve with the wrong hash is refused (409)")
    other = _token(False)
    if other:
        check(call("POST", f"/tasks/{task_id}/input", headers={"Authorization": f"Bearer {other}"}, json={"decision": "approve", "plan_hash": h})[0] == 403, "a non-superuser cannot approve (403)")
    code, c = call("POST", f"/tasks/{task_id}/cancel", json={"reason": "phase0 proof cleanup"})
    check(code == 200 and c["status"] == "cancelled", "cancel at the gate works")
    wait_for(task_id, lambda b: b["status"] == "cancelled")
    end = events(task_id)
    check(end["events"][-1]["event"]["code"] == "CANCELLED" and end["calmCard"]["status"] == "paused", "ends with RUN_ERROR CANCELLED and a paused card")
    check(call("POST", f"/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h})[0] == 409, "a cancelled run can no longer be approved (409)")
    print("PHASE0 PASS")


def phase1() -> None:
    key = f"prove-crew-live-{uuid.uuid4().hex[:8]}"
    code, h = start(key=key)
    check(code == 200, "crew started")
    wait_for(h["taskId"], gate)
    ev = events(h["taskId"])
    check(names(ev).count("hypercode.approval.required") == 1, "parked at the plan gate (one approval event)")
    print(f"PARKED_TASK={h['taskId']}")
    print(f"PARKED_KEY={key}")
    print(f"PARKED_NEXT_AFTER={ev['nextAfter']}")


def phase2(task_id: str, key: str, next_after: int) -> None:
    body = wait_for(task_id, gate, timeout=240)
    check(True, "after the restart the run is parked at the plan gate again (recovered)")
    ev = events(task_id)
    check(names(ev).count("hypercode.approval.required") == 1 and ev["nextAfter"] == next_after, "same events as before the restart: no duplicate approval, same last sequence")
    code, dup = start(key=key)
    check(code == 200 and dup["taskId"] == task_id and dup.get("deduplicated") is True, "a retried start after the restart returns the SAME task")
    h = plan_hash_of(body)
    check(call("POST", f"/tasks/{task_id}/input", json={"decision": "approve", "plan_hash": h})[0] == 200, "the exact plan hash is accepted")
    end = wait_for(task_id, lambda b: b["status"] in ("completed", "failed"), timeout=420)
    fin = events(task_id, after=ev["nextAfter"])
    check("hypercode.plan.sealed" in names(fin), "the approved plan was sealed")
    last = fin["events"][-1]["event"]
    if end["status"] == "completed":
        check(last["type"] == "RUN_FINISHED" and "hypercode.guard.verdict" in names(fin), "COMPLETED: RUN_FINISHED with a guard verdict")
        verdict = next(e["event"]["value"] for e in fin["events"] if e["event"].get("name") == "hypercode.guard.verdict")
        check(verdict["verdict"] in ("ALLOW", "BLOCK") and verdict["bundleHash"].startswith("sha256:"), f"guard decided {verdict['verdict']} with an evidence bundle hash")
        check(fin["calmCard"]["status"] in ("done", "blocked"), "Calm Card reflects the verdict")
    else:
        check(last["type"] == "RUN_ERROR" and "hypercode.guard.verdict" not in names(fin), "FAILED CLOSED: RUN_ERROR and no verdict from a stage that never ran")
        check(fin["calmCard"]["status"] == "blocked", "Calm Card says blocked")
        print(f"(reason: {str(end.get('error'))[:160]})")
    print("PHASE2 PASS")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase0"
    if phase == "phase0":
        phase0()
    elif phase == "phase1":
        phase1()
    elif phase == "phase2" and len(sys.argv) == 5:
        phase2(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        sys.exit("usage: phase0 | phase1 | phase2 <task_id> <key> <next_after>")
