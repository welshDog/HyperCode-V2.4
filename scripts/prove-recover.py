"""Live proof for hypercode.recover (Phase 2a). Runs INSIDE hypercode-core.

Controller prerequisites (host, once): two throwaway containers, then remove them afterwards:
  docker run -d --name zz-recover-proof   --label hypercode.recover=restartable \
      --health-cmd "exit 1" --health-interval 5s --health-retries 1 alpine sleep 3600
  docker run -d --name zz-recover-nolabel \
      --health-cmd "exit 1" --health-interval 5s --health-retries 1 alpine sleep 3600
  (wait ~20 s until both report unhealthy)

    docker exec -i hypercode-core python - phaseA  < scripts/prove-recover.py
    docker exec -i hypercode-core python - phaseB1 < scripts/prove-recover.py   # prints PARKED_TASK=<id>
    docker restart hypercode-core                                                # then wait healthy
    docker exec -i hypercode-core python - phaseB2 <id> < scripts/prove-recover.py

Prints only PASS/FAIL/INFO lines. Never prints a token. Read-only Docker GETs only.
"""

import sys
import time

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

ROOT = "http://localhost:8000"
BASE = ROOT + "/api/v1/operator"
TARGET = "zz-recover-proof"
NOLABEL = "zz-recover-nolabel"


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


def call(method, path, **kw):
    r = httpx.request(method, BASE + path, headers=HEADERS, timeout=30, **kw)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def docker_state(name):
    """Read-only GET via the socket proxy: (StartedAt, RestartCount) or None."""
    r = httpx.get(f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/{name}/json", timeout=10)
    if r.status_code != 200:
        return None
    j = r.json()
    return (j["State"]["StartedAt"], j["RestartCount"])


def check(ok, label):
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        sys.exit(1)


def wait_for(task_id, want, timeout=120):
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task_id}")
            last = body.get("status")
            if code == 200 and last in want:
                return body
        except httpx.HTTPError:
            pass
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for {sorted(want)} on {task_id}; last status={last}")


def start_recover():
    code, h = call("POST", "/tasks", json={"tool": "hypercode.recover", "arguments": {}})
    check(code == 200 and h.get("taskId"), "hypercode.recover returns a handle immediately")
    return h["taskId"]


def cancel_quiet(tid):
    try:
        call("POST", f"/tasks/{tid}/cancel", json={"reason": "proof cleanup"})
    except Exception:
        pass


def phaseA():
    before = docker_state(TARGET)
    check(before is not None, f"throwaway container {TARGET} exists")
    tid = start_recover()
    try:
        body = wait_for(tid, {"input_required"})
        ap = body["inputRequests"]["approval"]
        ctx = ap["context"]
        plan = ctx["proposal"]["plan"]
        check(plan["target"] == TARGET, f"proposal targets exactly {TARGET}")
        check(plan["action"] == "restart" and plan["run_id"] == tid, "plan is a restart bound to this run")
        check(ap["plan_hash"] == ctx["proposal"]["plan_hash"], "gate shows the plan_hash of the proposal")
        check(any(NOLABEL in x and "not_allowlisted" in x for x in ctx["not_eligible"]),
              f"unlabelled unhealthy {NOLABEL} is refused (not_allowlisted)")
        check(all(c["container"] != "hypercode-core" or not c["eligibility"]["allowed"]
                  for c in ctx["candidates"]), "no protected container is ever eligible")
        good = ap["plan_hash"]

        code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve"})
        check(code == 422, f"approve without plan_hash -> {code} (expected 422)")
        code, b = call("POST", f"/tasks/{tid}/input",
                       json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64})
        check(code == 409 and b.get("detail", {}).get("error") == "plan_hash_mismatch",
              f"approve with WRONG plan_hash -> {code} plan_hash_mismatch")
        time.sleep(3)
        _, still = call("GET", f"/tasks/{tid}")
        check(still["status"] == "input_required", "still parked after the rejected approvals")

        code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve", "plan_hash": good})
        check(code == 200, "approve with the shown plan_hash accepted")
        done = wait_for(tid, {"completed", "failed"})
        check(done["status"] == "completed", "run completed after approval")
        check("seal" in done["result"]["nodes"], "seal ran")
        check("authorize" in done["result"]["nodes"], "authorize ran as part of the flow")
        authz = done["result"]["report"]
        # Fix-round (final review, Important 2): restored -- `authz` (authorize's own result)
        # echoes 2a's plan_hash verbatim, so this is the live proof's own binding check that
        # what got sealed is exactly what the human approved (`good`), not just that `seal` ran.
        # Dropped when this block was first adapted for authorize's output; report only proved
        # authorize's own claims, never re-connected them back to 2a's approval.
        check(authz["plan_hash"] == good, "authorize's plan_hash matches the hash the human approved")
        check(authz["plan_hash"] != authz["governor_plan_hash"], "2a's hash and Governor's hash are never the same value")
        check(authz["minted"] is False, "Governor refused to mint (no grant exists) -- the correct outcome")
        check(authz["mode"] == "DRY_RUN", "requested mode was DRY_RUN")
        check(authz["verdict"]["decision"] == "ESCALATE", "Shepherd verdict was ESCALATE")
        check(authz["verdict"].get("risk_class") == "INFRASTRUCTURE_MUTATION", "risk class is INFRASTRUCTURE_MUTATION")
        db = SessionLocal()
        try:
            n = db.execute(
                text("SELECT count(*) FROM governance_ledger WHERE action='recover_plan_approved' "
                     "AND payload->>'run_id' = :r"), {"r": tid}).scalar()
        finally:
            db.close()
        check(n == 1, "exactly one Governance Ledger row for this run")
        db = SessionLocal()
        try:
            n2 = db.execute(
                text("SELECT count(*) FROM governance_ledger WHERE action='recover_authorization_attempted' "
                     "AND payload->>'run_id' = :r"), {"r": tid}).scalar()
        finally:
            db.close()
        check(n2 == 1, "exactly one authorize-attempt Governance Ledger row for this run")
        after = docker_state(TARGET)
        check(after == before, f"{TARGET} was NOT restarted (StartedAt/RestartCount unchanged)")
        r = httpx.get(f"{ROOT}/api/v1/flows/runs/{tid}", timeout=30)
        check(r.status_code == 200, "legacy unauthenticated run endpoint reachable")
        leaked = [k for e in r.json().get("history", []) for k in ("data", "context")
                  if k in (e.get("result") or {})]
        check(not leaked, "legacy endpoint history has no result.data / result.context")
    finally:
        cancel_quiet(tid)

    tid2 = start_recover()
    try:
        wait_for(tid2, {"input_required"})
        code, _ = call("POST", f"/tasks/{tid2}/input", json={"decision": "reject"})
        check(code == 200, "reject needs no plan_hash")
        end = wait_for(tid2, {"failed", "completed"})
        check(end["status"] == "failed" and "approval rejected" in (end.get("error") or ""),
              "rejected plan fails the run and seals nothing")
        check(docker_state(TARGET) == before, f"{TARGET} still not restarted after reject")
    finally:
        cancel_quiet(tid2)
    print("PASS: phaseA complete")


def phaseB1():
    tid = start_recover()
    body = wait_for(tid, {"input_required"})
    check(body["inputRequests"]["approval"]["plan_hash"], "run parked at the approval gate with a plan_hash")
    print(f"PARKED_TASK={tid}")


def phaseB2(tid):
    body = wait_for(tid, {"input_required"})
    print("INFO: parked task is visible again after the restart")
    good = body["inputRequests"]["approval"]["plan_hash"]
    code, _ = call("POST", f"/tasks/{tid}/input", json={"decision": "approve", "plan_hash": good})
    check(code == 200, "approval with the shown plan_hash accepted after the restart")
    done = wait_for(tid, {"completed", "failed"})
    # Same fix as phaseA: `report` is overwritten by the LAST completed node's data, which is
    # now `authorize` (no "sealed" key), not `seal` -- prove seal ran via `nodes` instead.
    check(done["status"] == "completed" and "seal" in done["result"]["nodes"],
          "sealed after an approval that survived a core restart")
    check(docker_state(TARGET) is not None, f"{TARGET} untouched")
    print("PASS: phaseB2 complete")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phaseA":
        phaseA()
    elif len(sys.argv) >= 2 and sys.argv[1] == "phaseB1":
        phaseB1()
    elif len(sys.argv) >= 3 and sys.argv[1] == "phaseB2":
        phaseB2(sys.argv[2])
    else:
        sys.exit("usage: phaseA | phaseB1 | phaseB2 <task_id>")
