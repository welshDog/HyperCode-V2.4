"""LOCAL multi-process proof for HyperCrew (no Docker, no LLM agents). Run from backend/:

    cd backend && PYTHONPATH=.:.. python ../scripts/prove-crew-local.py

Real: hypercode-core (operator API, HyperFlow runner, boot-time recovery), hypercode-mcp-server, and a real
MCP client speaking the real SSE wire protocol. A REAL process restart of core (SIGTERM, then start again on
the same database file) is performed while a run is parked at the approval gate.
Stand-ins: sqlite instead of Postgres, no Redis, the agent-key lookup replaced by scripts/crew_proof_harness.py
(human auth is the real JWT path), and scripts/crew_proof_stub_orchestrator.py instead of crew-orchestrator.
This is NOT the live proof — scripts/prove-crew.py is. It exists so the whole path can be proved anywhere.
Prints PASS/FAIL lines only; exits non-zero on the first failure.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx
from app.core.security import create_access_token
from mcp import ClientSession
from mcp.client.sse import sse_client

ROOT = Path(__file__).resolve().parents[1]
STUB, CORE, MCP = 18081, 18000, 18823
CORE_URL = f"http://127.0.0.1:{CORE}"
GOAL = "add a health endpoint to the API"
RUN = uuid.uuid4().hex[:8]
procs: dict[str, subprocess.Popen] = {}
tmp = Path(tempfile.mkdtemp(prefix="prove-crew-"))


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label, flush=True)
    if not ok:
        raise SystemExit(1)


def env_for(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": f"{ROOT / 'backend'}:{ROOT}", "OTEL_SDK_DISABLED": "true", "SAFETY_SHEPHERD_MODE": "off",
        "HYPERCODE_DB_URL": f"sqlite:///{tmp / 'core.db'}", "HYPERCODE_REDIS_URL": "redis://127.0.0.1:1/0",
        "ORCHESTRATOR_URL": f"http://127.0.0.1:{STUB}", "STUB_COUNT_FILE": str(tmp / "stub-calls.txt"),
        "HYPERFLOW_APPROVAL_POLL_SECONDS": "0.2", "CREW_MIN_AVAILABLE_MB": "0",
    })
    env.update(extra)
    return env


def spawn(name: str, args: list[str], **extra: str) -> None:
    with open(tmp / f"{name}.log", "ab") as log:  # the child inherits its own copy of the descriptor
        procs[name] = subprocess.Popen(
            args, cwd=ROOT / "backend", env=env_for(**extra), stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )


def stop(name: str) -> None:
    p = procs.pop(name, None)
    if p is not None and p.poll() is None:
        os.killpg(p.pid, signal.SIGTERM)  # the same signal `docker restart` sends
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)


def wait_http(url: str, ok=lambda r: r.status_code < 500, timeout: float = 90) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if ok(httpx.get(url, timeout=3)):
                return
        except httpx.HTTPError:
            pass  # the server is not accepting connections yet; keep trying until the timeout
        time.sleep(0.5)
    raise SystemExit(f"FAIL: timed out waiting for {url} (logs in {tmp})")


UVICORN = [sys.executable, "-m", "uvicorn"]


def start_core() -> None:
    spawn("core", UVICORN + ["crew_proof_harness:app", "--app-dir", str(ROOT / "scripts"), "--host", "127.0.0.1", "--port", str(CORE)])
    wait_http(f"{CORE_URL}/api/v1/operator/tasks/nope", ok=lambda r: r.status_code in (401, 404))  # up and answering


def start_stub() -> None:
    spawn("stub", UVICORN + ["crew_proof_stub_orchestrator:app", "--app-dir", str(ROOT / "scripts"), "--host", "127.0.0.1", "--port", str(STUB)])
    wait_http(f"http://127.0.0.1:{STUB}/health")


def start_mcp() -> None:
    code = (
        "import importlib.util, uvicorn;"
        f"s=importlib.util.spec_from_file_location('srv', r'{ROOT / 'services/hypercode-mcp-server/server.py'}');"
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m);"
        f"uvicorn.run(m.mcp.sse_app(), host='127.0.0.1', port={MCP}, log_level='warning')"
    )
    spawn("mcp", [sys.executable, "-c", code], HYPERCODE_CORE_URL=CORE_URL, HYPERCODE_AGENT_KEY="proof-key")
    wait_http(f"http://127.0.0.1:{MCP}/health")


def _as(headers: dict[str, str], method: str, path: str, **kw) -> httpx.Response:
    return httpx.request(method, f"{CORE_URL}/api/v1/operator{path}", headers=headers, timeout=30, **kw)


def human(method: str, path: str, **kw) -> httpx.Response:  # user 1: a real JWT for the seeded superuser
    return _as({"Authorization": f"Bearer {create_access_token(subject=1)}"}, method, path, **kw)


def normal_user(method: str, path: str, **kw) -> httpx.Response:  # user 2: a real JWT, not a superuser
    return _as({"Authorization": f"Bearer {create_access_token(subject=2)}"}, method, path, **kw)


def agent(method: str, path: str, **kw) -> httpx.Response:
    return _as({"X-Agent-Key": "proof-key"}, method, path, **kw)


def nobody(method: str, path: str, **kw) -> httpx.Response:
    return _as({}, method, path, **kw)


def calls(kind: str) -> int:
    f = tmp / "stub-calls.txt"
    return f.read_text().split().count(kind) if f.exists() else 0


async def tool(session: ClientSession, name: str, args: dict) -> dict:
    res = await session.call_tool(name, args)
    if getattr(res, "structuredContent", None):
        return res.structuredContent.get("result", res.structuredContent) if "result" in res.structuredContent else res.structuredContent
    return json.loads(res.content[0].text)


async def poll(session: ClientSession, task_id: str, want, timeout: float = 30, after: int = -1) -> dict:
    end, last = time.time() + timeout, None
    while time.time() < end:
        last = await tool(session, "hypercode_crew_status", {"task_id": task_id, "after": after})
        if want(last):
            return last
        await asyncio.sleep(0.3)
    raise SystemExit(f"FAIL: timed out polling {task_id}; last status={last and last.get('status')}")


def at_handover_gate(p: dict) -> bool:
    return p["status"] == "input_required" and p["calmCard"]["next_action"].startswith("Read the handover draft")


async def answer_handover(session: ClientSession, task_id: str, decision: str = "approve") -> str:
    """The run ends with a handover gate. Approve with the DRAFT's own hash (the same rule as the plan)."""
    gate = await poll(session, task_id, at_handover_gate, timeout=45)
    h = next(e["event"]["value"]["planHash"] for e in gate["events"]
             if e["event"].get("name") == "hypercode.approval.required" and e["event"]["value"]["node"] == "approve_scribe")
    body = {"decision": decision, **({"plan_hash": h} if decision == "approve" else {})}
    check(human("POST", f"/tasks/{task_id}/input", json=body).status_code == 200, f"handover draft answered: {decision}")
    return h


def names(payload: dict) -> list:
    return [e["event"].get("name") for e in payload["events"] if e["event"]["type"] == "CUSTOM"]


def at_gate(p: dict) -> bool:
    return p["status"] == "input_required" and "hypercode.approval.required" in names(p)


async def main() -> None:
    start_stub(); start_core(); start_mcp()
    check(True, "stub orchestrator, hypercode-core and hypercode-mcp-server are up")

    async with sse_client(f"http://127.0.0.1:{MCP}/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            check({"hypercode_crew_start", "hypercode_crew_status"} <= tools, "MCP lists the crew tools over the real SSE protocol")
            check(not any("approve" in t or "input" in t for t in tools), "no MCP tool can approve a plan")

            key = f"prove-crew-{RUN}-main"
            started = await tool(session, "hypercode_crew_start", {"goal": GOAL, "idempotency_key": key})
            task_id = started["taskId"]
            check(started["status"] == "working", "crew_start returned a task handle immediately")
            parked = await poll(session, task_id, at_gate)
            before = parked
            plan_hash = next(e["event"]["value"]["planHash"] for e in parked["events"] if e["event"].get("name") == "hypercode.approval.required")
            check(plan_hash.startswith("sha256:") and parked["calmCard"]["status"] == "waiting_on_you", "run parks at the plan gate with a hash and a Calm Card saying 'waiting on you'")
            check(parked["events"][0]["event"]["type"] == "RUN_STARTED" and [e["seq"] for e in parked["events"]] == list(range(len(parked["events"]))), "events start with RUN_STARTED, sequence is contiguous")
            ask = json.dumps([e for e in parked["events"] if e["event"].get("name") == "hypercode.approval.required"])
            check(GOAL not in ask and '"stages"' not in ask and "planHash" in ask, "the approval event carries the hash, not the plan body")

            dup = await tool(session, "hypercode_crew_start", {"goal": GOAL, "idempotency_key": key})
            check(dup["taskId"] == task_id and dup.get("deduplicated") is True, "retrying crew_start with the same key returns the SAME task")
            body = {"decision": "approve", "plan_hash": plan_hash}
            check(nobody("POST", f"/tasks/{task_id}/input", json=body).status_code == 401, "no credentials at all: refused (401)")
            check(agent("POST", f"/tasks/{task_id}/input", json=body).status_code == 403, "an agent identity cannot approve (403)")
            check(normal_user("POST", f"/tasks/{task_id}/input", json=body).status_code == 403, "a non-superuser cannot approve (403)")

            # ── REAL restart of core while parked ──
            stop("core")
            check("core" not in procs, "core process stopped (SIGTERM)")
            start_core()
            log = (tmp / "core.log").read_text(errors="replace")
            check(f"run={task_id} action=resume" in log, "boot recovery log: this run was RESUMED after the restart")
            after = await poll(session, task_id, at_gate)
            check(after["events"][: len(before["events"])] == before["events"], "replay across the real restart is exact (same events, same order)")
            check(names(after).count("hypercode.approval.required") == 1 and after["nextAfter"] == before["nextAfter"], "no phantom duplicate approval event after the restart")
            check(human("GET", f"/tasks/{task_id}").json()["inputRequests"]["approval"]["plan_hash"] == plan_hash, "still the same plan hash")

            url = f"/tasks/{task_id}/input"
            check(human("POST", url, json={"decision": "approve", "plan_hash": "sha256:" + "0" * 64}).status_code == 409, "wrong plan hash is refused (409)")
            check(human("POST", url, json={"decision": "approve"}).status_code == 422, "missing plan hash is refused (422)")
            check(human("POST", url, json={"decision": "approve", "plan_hash": plan_hash}).status_code == 200, "the exact plan hash is accepted")

            # ── Scribe: a draft handover, a gate bound to the draft's own hash, a docs-only DRAFT PR ──
            gate = await poll(session, task_id, at_handover_gate, timeout=45)
            drafted = [e["event"]["value"] for e in gate["events"] if e["event"].get("name") == "hypercode.handover.drafted"]
            check(len(drafted) == 1 and all(f.startswith(("docs/NEXT_SESSION_HANDOVER_", "docs/crew-proposals/")) for f in drafted[0]["files"]), "the Scribe drafted docs-only files and parked at its own gate")
            ctx = human("GET", f"/tasks/{task_id}").json()["inputRequests"]["approval"]
            draft_hash = ctx["plan_hash"]
            check(ctx["node"] == "approve_scribe" and draft_hash != plan_hash and draft_hash.startswith("sha256:"), "the handover gate has its own hash, not the plan's")
            check(human("POST", url, json={"decision": "approve"}).status_code == 422, "approving the draft without its hash is refused (422)")
            check(human("POST", url, json={"decision": "approve", "plan_hash": plan_hash}).status_code == 409, "approving the draft with the PLAN's hash is refused (409)")
            check(human("POST", url, json={"decision": "approve", "plan_hash": draft_hash}).status_code == 200, "the exact draft hash is accepted")

            done = await poll(session, task_id, lambda p: p["done"], timeout=45)
            seen = await poll(session, task_id, lambda p: True, after=before["nextAfter"])
            check(done["status"] == "completed" and done["calmCard"]["status"] == "done", "run completed; Calm Card says done")
            check(seen["events"][-1]["event"]["type"] == "RUN_FINISHED", "events end with RUN_FINISHED")
            check({"hypercode.approval.resolved", "hypercode.plan.sealed", "hypercode.guard.verdict"} <= set(names(seen)), "approval, seal and guard verdict events all arrived")
            verdict = next(e["event"]["value"] for e in seen["events"] if e["event"].get("name") == "hypercode.guard.verdict")
            check(verdict["verdict"] == "ALLOW" and verdict["bundleHash"].startswith("sha256:"), "guard allowed it, with an evidence bundle hash")
            check(calls("crew_build") == 1 and calls("crew_verify") == 1, "builder and verifier were each asked exactly once (no double dispatch)")
            check([e["seq"] for e in seen["events"]] == list(range(before["nextAfter"] + 1, seen["nextAfter"] + 1)), "replay with `after` returns only what was missed")

            # ── Quest Settler: paid once, to the approving human, from the guard-ALLOWed run ──
            import sqlite3

            with sqlite3.connect(tmp / "core.db") as conn:
                rows = conn.execute("select source_id, user_id, status, xp from quest_settlements where quest_id = 'crew_run'").fetchall()
                wallet = conn.execute("select xp, coins from broski_wallets where user_id = 1").fetchone()
                paid = conn.execute("select count(*) from broski_transactions where reason = 'Quest: crew run'").fetchone()[0]
            conn.close()
            check(rows == [(f"{task_id}:crew_run", 1, "awarded", 20)], "settled exactly once, to the approving human (user 1), 20 XP")
            check(wallet is not None and wallet[0] >= 20 and paid == 1, "the human's wallet was credited by one traceable transaction")
            check("hypercode.quest.settled" in names(seen), "the quiet win arrived as one event")
            check(any("+20 XP" in line for line in done["calmCard"]["tldr"]), "the Calm Card shows one quiet XP line")

            # ── publish: with no GitHub token configured it must say so and open nothing ──
            published = [e["event"]["value"] for e in seen["events"] if e["event"].get("name") == "hypercode.handover.published"]
            check(len(published) == 1 and published[0]["prOpened"] is False and published[0]["status"] == "not_configured", "no GitHub token: it says the draft stayed in the run, and opened no PR")
            check(done["calmCard"]["tldr"][-1] == "Handover draft kept in this run" or "Handover draft kept in this run" in done["calmCard"]["tldr"], "the Calm Card says so too")
            with sqlite3.connect(tmp / "core.db") as conn2:
                hrow = conn2.execute("select status, xp, user_id from quest_settlements where quest_id = 'handover_written'").fetchall()
                badge = conn2.execute("select count(*) from broski_user_achievements where achievement_slug = 'handover_written'").fetchone()[0]
                audit = conn2.execute("select approved_by from governance_ledger where action = 'crew_handover_published'").fetchall()
            conn2.close()
            check(hrow == [("awarded", 0, 1)] and badge == 1, "Handover Written unlocked once, for the human who approved the draft")
            check(audit == [("proof-super@example.com",)], "the publish was written to the Governance Ledger with the approver")

            # ── Morning Card ──
            m = human("GET", "/morning").json()
            mc = m["calmCard"]
            check(m["light"] in ("green", "amber", "red") and len(mc["tldr"]) <= 5 and any("verified run" in t for t in mc["tldr"]), "the Morning Card has one light, at most 5 lines, and yesterday's win")
            check(agent("GET", "/morning").status_code == 200 and not any("XP" in t for t in agent("GET", "/morning").json()["calmCard"]["tldr"]), "an agent key can read it but sees no one's XP")

            # ── cancel at the gate, through MCP ──
            c = await tool(session, "hypercode_crew_start", {"goal": "write a cancelled thing", "idempotency_key": f"prove-crew-{RUN}-cancel"})
            cplan = await poll(session, c["taskId"], at_gate)
            cancelled = await tool(session, "hypercode_task_cancel", {"task_id": c["taskId"], "reason": "proof cancel"})
            check(cancelled.get("status") == "cancelled", "MCP cancel works")
            cend = await poll(session, c["taskId"], lambda p: p["done"])
            check(cend["events"][-1]["event"]["code"] == "CANCELLED" and cend["calmCard"]["status"] == "paused", "cancelled run ends with RUN_ERROR CANCELLED and a paused card")
            cplan_hash = next(e["event"]["value"]["planHash"] for e in cplan["events"] if e["event"].get("name") == "hypercode.approval.required")
            check(human("POST", f"/tasks/{c['taskId']}/input", json={"decision": "approve", "plan_hash": cplan_hash}).status_code == 409, "a cancelled run can no longer be approved")

            # ── Panic: a durable hold that survives a REAL restart and needs a human to release ──
            pk = await tool(session, "hypercode_crew_start", {"goal": "hold this one with panic", "idempotency_key": f"prove-crew-{RUN}-panic"})
            pgate = await poll(session, pk["taskId"], at_gate)
            phash = next(e["event"]["value"]["planHash"] for e in pgate["events"] if e["event"].get("name") == "hypercode.approval.required")
            panic = human("POST", "/panic").json()
            check(panic["saved"] is True and pk["taskId"] in [x["taskId"] for x in panic["paused"]], "Panic saved and paused the run")
            check(panic["message"] == "Saved. Nothing is running. Take your time.", "Panic tells you plainly that nothing is running")
            pbody = {"decision": "approve", "plan_hash": phash}
            check(human("POST", f"/tasks/{pk['taskId']}/input", json=pbody).status_code == 409, "a paused run cannot be approved (409)")
            check(agent("POST", f"/tasks/{pk['taskId']}/resume").status_code == 403, "an agent key cannot resume (403)")
            again = await tool(session, "hypercode_crew_pause", {"task_id": pk["taskId"], "reason": "agent pause"})
            check(again.get("alreadyPaused") is True, "an agent can pause (idempotent), via MCP")
            stop("core")
            start_core()
            held = await poll(session, pk["taskId"], lambda p: p.get("paused") is True and p["status"] == "working")
            check(held["calmCard"]["status"] == "paused" and held["calmCard"]["tldr"][-1] == "Paused. Nothing is running.", "after a REAL restart the hold is still there and the card says nothing is running")
            check(human("POST", f"/tasks/{pk['taskId']}/input", json=pbody).status_code == 409, "still cannot be approved after the restart")
            check(pk["taskId"] in [x["taskId"] for x in human("GET", "/panic").json()["paused"]], "GET /panic lists what is held")
            check(pk["taskId"] in human("POST", "/panic/resume").json()["resumed"], "a human releases the hold")
            await poll(session, pk["taskId"], at_gate)
            check(human("POST", f"/tasks/{pk['taskId']}/input", json=pbody).status_code == 200, "released: the same plan hash is accepted")
            await answer_handover(session, pk["taskId"])
            pdone = await poll(session, pk["taskId"], lambda p: p["done"], timeout=45)
            check(pdone["status"] == "completed", "the held run then completed")

            # ── orchestrator down: fail closed ──
            stop("stub")
            before_calls = calls("crew_build")
            d = await tool(session, "hypercode_crew_start", {"goal": "orchestrator is down for this one", "idempotency_key": f"prove-crew-{RUN}-down"})
            dgate = await poll(session, d["taskId"], at_gate)
            dhash = next(e["event"]["value"]["planHash"] for e in dgate["events"] if e["event"].get("name") == "hypercode.approval.required")
            check(human("POST", f"/tasks/{d['taskId']}/input", json={"decision": "approve", "plan_hash": dhash}).status_code == 200, "approved while the orchestrator is down")
            dend = await poll(session, d["taskId"], lambda p: p["done"], timeout=45)
            check(dend["status"] == "failed" and dend["calmCard"]["status"] == "blocked", "run FAILED closed (not a mocked green)")
            check(dend["events"][-1]["event"]["code"] == "RUN_FAILED" and "hypercode.guard.verdict" not in names(dend), "no guard verdict from a stage that never ran")
            check(calls("crew_build") == before_calls, "nothing was dispatched")
    print("ALL PASS", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseExceptionGroup:  # a check() failed inside the MCP client's task group; it already printed FAIL
        sys.exit(1)
    finally:
        for n in list(procs):
            stop(n)
        print(f"(logs kept in {tmp})")
