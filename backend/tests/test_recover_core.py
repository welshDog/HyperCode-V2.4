"""BROski recover — pure candidate/evidence/plan logic."""

import asyncio

from app.broski_operator import recover


def S(name, state, status, labels=None, cid=None):
    return {"Id": cid or (name.replace("-", "")[:12].ljust(12, "0")), "Names": ["/" + name],
            "State": state, "Status": status, "Labels": labels or {}}


def D(oom=False, exit_code=0, probes=("boom",), restarts=2):
    return {
        "RestartCount": restarts,
        "State": {"OOMKilled": oom, "ExitCode": exit_code, "StartedAt": "s", "FinishedAt": "f",
                  "Health": {"Status": "unhealthy", "Log": [{"Output": p} for p in probes]}},
    }


def test_reason_from_summary_table():
    r = recover.reason_from_summary
    assert r(S("a", "running", "Up 2 hours (unhealthy)")) == "unhealthy"
    assert r(S("a", "running", "Up 2 hours (healthy)")) is None
    assert r(S("a", "restarting", "Restarting (1) 5 seconds ago")) == "restarting"
    assert r(S("a", "exited", "Exited (1) 3 hours ago")) == "crashed"
    assert r(S("a", "exited", "Exited (139) 3 hours ago")) == "crashed"
    # Review focus 2: stopped on purpose is never a candidate
    assert r(S("a", "exited", "Exited (0) 3 hours ago")) is None
    assert r(S("a", "exited", "Exited (143) 3 hours ago")) is None
    # 137 is SIGKILL: could be OOM or a `docker stop` escalation -> needs the detail
    assert r(S("a", "exited", "Exited (137) 3 hours ago")) == "needs_detail"
    assert r(S("a", "exited", "weird status")) is None
    assert r({}) is None


def _gather(summaries, details):
    async def get_detail(cid):
        return details.get(cid)
    return asyncio.run(recover.gather_candidates(summaries, get_detail))


def test_gather_137_only_when_oom_killed():
    oom = S("agent-mcp-bridge", "exited", "Exited (137) 1 hour ago", cid="aaaaaaaaaaaa")
    stopped = S("memstream", "exited", "Exited (137) 1 hour ago", cid="bbbbbbbbbbbb")
    out = _gather([oom, stopped], {"aaaaaaaaaaaa": D(oom=True, exit_code=137),
                                   "bbbbbbbbbbbb": D(oom=False, exit_code=137)})
    assert [c["container"] for c in out] == ["agent-mcp-bridge"]
    assert out[0]["reason"] == "crashed" and out[0]["evidence"]["oom_killed"] is True


def test_gather_137_with_no_detail_is_excluded():
    s = S("agent-mcp-bridge", "exited", "Exited (137) 1 hour ago", cid="aaaaaaaaaaaa")
    assert _gather([s], {}) == []


def test_gather_ranks_unhealthy_then_restarting_then_crashed():
    sums = [
        S("zz-crashed", "exited", "Exited (1) 1 hour ago", cid="c1c1c1c1c1c1"),
        S("zz-restarting", "restarting", "Restarting (1) 2s ago", cid="c2c2c2c2c2c2"),
        S("zz-unhealthy", "running", "Up 1 hour (unhealthy)", cid="c3c3c3c3c3c3"),
    ]
    out = _gather(sums, {})
    assert [c["reason"] for c in out] == ["unhealthy", "restarting", "crashed"]


def test_gather_caps_detail_lookups():
    sums = [S(f"zz-{i:02d}", "running", "Up (unhealthy)", cid=f"{i:012x}") for i in range(15)]
    calls = []

    async def get_detail(cid):
        calls.append(cid)
        return D()

    out = asyncio.run(recover.gather_candidates(sums, get_detail))
    assert len(calls) == recover.MAX_DETAIL and len(out) == 15


def test_eligibility_is_attached_and_never_list_wins():
    sums = [S("hypercode-core", "running", "Up (unhealthy)", labels={"hypercode.recover": "restartable"},
              cid="d1d1d1d1d1d1"),
            S("skillweaver", "running", "Up (unhealthy)", cid="d2d2d2d2d2d2")]
    out = {c["container"]: c for c in _gather(sums, {})}
    assert out["hypercode-core"]["eligibility"]["blocked_by"] == "never_list"
    assert out["skillweaver"]["eligibility"]["allowed"] is True


def test_evidence_caps_probes_clips_and_scrubs():
    long = "x" * 500
    detail = D(probes=("one", "two", "redis://:hunter2@cache:6379 failed", "password=abc123 " + long))
    ev = recover.build_evidence(S("a", "running", "Up (unhealthy)"), detail)
    assert len(ev["health_probes"]) == 3            # last 3 only
    joined = " ".join(ev["health_probes"])
    assert "hunter2" not in joined and "abc123" not in joined
    assert all(len(p) <= 200 for p in ev["health_probes"])
    assert ev["restart_count"] == 2 and ev["oom_killed"] is False


def test_evidence_without_detail_uses_summary_only():
    ev = recover.build_evidence(S("a", "restarting", "Restarting (1) 2s ago"), None)
    assert ev["state"] == "restarting" and ev["health_probes"] == [] and ev["restart_count"] is None


def test_scrub_text():
    assert "hunter2" not in recover.scrub_text("redis://:hunter2@cache:6379/0")
    assert "abc" not in recover.scrub_text("PASSWORD=abc")


def test_plan_hash_is_canonical_stable_and_run_bound():
    cand = {"container": "skillweaver", "reason": "unhealthy", "evidence": {"a": 1, "b": 2}}
    p1 = recover.build_plan(cand, "run-1")
    p2 = recover.build_plan({**cand, "evidence": {"b": 2, "a": 1}}, "run-1")
    assert recover.plan_hash(p1) == recover.plan_hash(p2)          # key order does not matter
    assert recover.plan_hash(p1).startswith("sha256:") and len(recover.plan_hash(p1)) == 7 + 64
    assert recover.plan_hash(recover.build_plan(cand, "run-2")) != recover.plan_hash(p1)   # run-bound
    assert recover.plan_hash({**p1, "target": "other"}) != recover.plan_hash(p1)           # tamper-evident
    assert p1["version"] == 1 and p1["action"] == "restart" and p1["target"] == "skillweaver"


def test_dependents_from_compose_labels():
    target = S("redis", "running", "Up", labels={"com.docker.compose.service": "redis"})
    others = [
        S("a", "running", "Up", labels={"com.docker.compose.service": "a",
                                         "com.docker.compose.depends_on": "redis:service_healthy:false,db:service_started:false"}),
        S("b", "running", "Up", labels={"com.docker.compose.service": "b",
                                         "com.docker.compose.depends_on": "db:service_started:false"}),
    ]
    assert recover.dependents_of(target, [target] + others) == ["a"]
    assert recover.dependents_of(target, [target]) is None  # no depends_on labels anywhere -> unknown


def test_build_report_picks_first_eligible_and_lists_the_rest():
    cands = [
        {"container": "hypercode-core", "state": "running", "reason": "unhealthy", "evidence": {},
         "eligibility": {"allowed": False, "basis": None, "blocked_by": "never_list"}},
        {"container": "skillweaver", "state": "running", "reason": "unhealthy", "evidence": {"x": 1},
         "eligibility": {"allowed": True, "basis": "allow_list", "blocked_by": None}},
    ]
    rep = recover.build_report(cands, "run-9", ["note"])
    assert rep["ok"] is True and rep["has_proposal"] is True
    assert rep["proposal"]["plan"]["target"] == "skillweaver"
    assert rep["proposal"]["plan_hash"] == recover.plan_hash(rep["proposal"]["plan"])
    assert rep["not_eligible"] == ["hypercode-core: never_list"] and rep["notes"] == ["note"]


def test_build_report_with_nothing_to_recover():
    rep = recover.build_report([], "run-9", [])
    assert rep["has_proposal"] is False and rep["proposal"] is None and rep["candidates"] == []
