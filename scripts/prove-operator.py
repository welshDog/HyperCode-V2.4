"""Live proof for the BROski operator. Runs INSIDE hypercode-core so tokens never leave it:

    docker exec -i hypercode-core python - phase1 < scripts/prove-operator.py
    docker restart hypercode-core        # (after phase1 prints PARKED_TASK=<id>)
    docker exec -i hypercode-core python - phase2 <id> < scripts/prove-operator.py

phase1: inspect -> completed report; cancel proof; then parks a two-gate task at input_required.
phase2: (after the restart) the parked task resumes at its gate, is approved twice, completes.
Prints only ids and PASS/FAIL lines. Never prints the token.
"""

import sys
import time

import httpx

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

BASE = "http://localhost:8000/api/v1/operator"


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
                if b["status"] == "input_required" and b["inputRequests"]["approval"]["node"] == "finish":
                    break
                time.sleep(2)
            else:
                sys.exit("FAIL: second gate never appeared")
    done = wait_for(task_id, {"completed", "failed"})
    check(done["status"] == "completed", "task completed after approvals that survived a core restart")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phase1":
        phase1()
    elif len(sys.argv) >= 3 and sys.argv[1] == "phase2":
        phase2(sys.argv[2])
    else:
        sys.exit("usage: phase1 | phase2 <task_id>")
