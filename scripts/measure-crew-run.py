"""ONE live HyperCrew run, measured. Runs INSIDE hypercode-core (mints its own token there; nothing secret is printed):

    docker exec -e MEASURE_GOAL="add a version endpoint to the API" -i hypercode-core python - < scripts/measure-crew-run.py

Starts a crew run, approves the plan with its exact hash, ALWAYS rejects the handover gate (so no draft PR can ever open),
waits for the end, and prints ONE final line:  RESULT {json}  with outcome, guard verdict, failed checks, timings.
Outcomes: ALLOW | BLOCK (failed checks listed) | FAILED (run error, no verdict) | STUCK (cancelled after the timeout).
A run that does not finish is cancelled so nothing is left parked. Side effect of an ALLOW: the Quest Settler awards XP/coins
to the owner account, exactly as a normal run does.
"""
import json
import os
import sys
import time
import uuid

import httpx

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

BASE = os.getenv("MEASURE_CORE_URL", "http://localhost:8000") + "/api/v1/operator"
GOAL = os.getenv("MEASURE_GOAL", "add a version endpoint to the API")
RUN_TIMEOUT_S = int(os.getenv("MEASURE_TIMEOUT_S", "420"))

_db = SessionLocal()
_user = _db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).first()
if _user is None:
    sys.exit("no active superuser")
_H = {"Authorization": f"Bearer {create_access_token(subject=_user.id)}"}
_db.close()


def call(method, path, **kw):
    r = httpx.request(method, BASE + path, headers=_H, timeout=30, **kw)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


def approval_node(b):
    return ((b.get("inputRequests") or {}).get("approval") or {}).get("node")


def wait(task, pred, timeout):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task}")
            if code == 200 and body:
                last = body
                if pred(body):
                    return body
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return last


t0 = time.time()
res = {"goal": GOAL, "outcome": None, "verdict": None, "failed_checks": [], "error": None, "seconds": None, "stage_seconds": {}}
task = None
try:
    code, h = call("POST", "/tasks", json={"tool": "hypercode.crew", "arguments": {"goal": GOAL}, "idempotency_key": f"measure-{uuid.uuid4().hex[:10]}"})
    if code != 200:
        res.update(outcome="FAILED", error=f"start refused: HTTP {code}")
        raise SystemExit
    task = h["taskId"]
    res["task"] = task[:8]
    gate = wait(task, lambda b: b["status"] == "input_required" and approval_node(b) == "approve", 180)
    if not gate or approval_node(gate) != "approve":
        res.update(outcome="STUCK", error="never reached the plan gate")
        raise SystemExit
    res["stage_seconds"]["plan"] = round(time.time() - t0)
    plan_hash = gate["inputRequests"]["approval"]["plan_hash"]
    code, _ = call("POST", f"/tasks/{task}/input", json={"decision": "approve", "plan_hash": plan_hash})
    if code != 200:
        res.update(outcome="FAILED", error=f"plan approval refused: HTTP {code}")
        raise SystemExit
    t1 = time.time()
    end = wait(task, lambda b: b["status"] in ("completed", "failed", "cancelled") or (b["status"] == "input_required" and approval_node(b) == "approve_scribe"), RUN_TIMEOUT_S)
    if end and end["status"] == "input_required" and approval_node(end) == "approve_scribe":
        call("POST", f"/tasks/{task}/input", json={"decision": "reject"})  # ALWAYS skip the handover: opens nothing
        end = wait(task, lambda b: b["status"] in ("completed", "failed", "cancelled"), 120)
    res["stage_seconds"]["build_to_end"] = round(time.time() - t1)
    if not end or end["status"] not in ("completed", "failed"):
        res.update(outcome="STUCK", error=f"status={(end or {}).get('status')} after {RUN_TIMEOUT_S}s")
        raise SystemExit
    code, ev = call("GET", f"/tasks/{task}/events", params={"after": -1})
    verdict = None
    for e in (ev or {}).get("events", []):
        x = e["event"]
        if x.get("type") == "CUSTOM" and x.get("name") == "hypercode.guard.verdict":
            verdict = x["value"]
    if end["status"] == "completed" and verdict:
        res.update(outcome=verdict["verdict"], verdict=verdict["verdict"], failed_checks=verdict.get("failedChecks") or [])
        # the verifier's own words for a BLOCK live only in the report detail
        rep = ((end.get("result") or {}).get("report") or {}).get("checks") or []
        res["verifier_detail"] = next((c.get("detail") for c in rep if c.get("name") == "verifier_verdict"), None)
    else:
        res.update(outcome="FAILED", error=str(end.get("error"))[:200])
except SystemExit:
    pass
except Exception as exc:  # noqa: BLE001 - report, never hide
    res.update(outcome=res["outcome"] or "FAILED", error=f"{type(exc).__name__}: {str(exc)[:160]}")
finally:
    if task and res["outcome"] in ("STUCK", None):
        call("POST", f"/tasks/{task}/cancel", json={"reason": "measure-crew-run: timed out, cleaning up"})
        res["cancelled_cleanup"] = True
    res["seconds"] = round(time.time() - t0)
    print("RESULT " + json.dumps(res))
