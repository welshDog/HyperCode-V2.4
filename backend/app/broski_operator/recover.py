"""Pure logic for `hypercode.recover` (Phase 2a): candidate rules, evidence, plan + plan_hash.

No IO in this module except the injected ``get_detail`` coroutine in ``gather_candidates``.
Nothing here can mutate Docker. Container ids are only ever passed to ``get_detail``.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Awaitable, Callable, Optional

from app.broski_operator.recover_policy import classify

MAX_DETAIL = 10
PLAN_VERSION = 1
_PROBES = 3
_PROBE_CAP = 200
_MAX_DEPENDENTS = 20
_QUIET_EXITS = {0, 143}          # clean stop / SIGTERM: stopped on purpose, never a candidate
_KILLED_EXIT = 137               # SIGKILL: OOM or a `docker stop` escalation -> needs detail
_RANK = {"unhealthy": 0, "restarting": 1, "crashed": 2}
_EXITED = re.compile(r"Exited \((\d+)\)")


def scrub_text(msg: str) -> str:
    """Remove URL userinfo and password= fragments from free text."""
    msg = re.sub(r"://[^/\s@]*@", "://***@", msg or "")
    return re.sub(r"(?i)\b(password|passwd)=\S+", r"\1=***", msg)


def _name(summary: dict[str, Any]) -> str:
    return ((summary.get("Names") or ["?"])[0] or "?").lstrip("/")


def reason_from_summary(summary: dict[str, Any]) -> Optional[str]:
    state = summary.get("State")
    status = summary.get("Status") or ""
    if state == "restarting":
        return "restarting"
    if state == "running" and "(unhealthy)" in status:
        return "unhealthy"
    if state == "exited":
        m = _EXITED.search(status)
        if not m:
            return None
        code = int(m.group(1))
        if code in _QUIET_EXITS:
            return None
        if code == _KILLED_EXIT:
            return "needs_detail"
        return "crashed"
    return None


def build_evidence(summary: dict[str, Any], detail: Optional[dict[str, Any]]) -> dict[str, Any]:
    st = (detail or {}).get("State") or {}
    health = st.get("Health") or {}
    probes = [
        scrub_text(str(p.get("Output") or ""))[:_PROBE_CAP]
        for p in (health.get("Log") or [])[-_PROBES:]
    ]
    return {
        "state": summary.get("State"),
        "status": scrub_text(str(summary.get("Status") or ""))[:80],
        "exit_code": st.get("ExitCode"),
        "oom_killed": bool(st.get("OOMKilled")),
        "restart_count": (detail or {}).get("RestartCount"),
        "started_at": st.get("StartedAt"),
        "finished_at": st.get("FinishedAt"),
        "health_status": health.get("Status"),
        "health_probes": probes,
    }


def dependents_of(summary: dict[str, Any], summaries: list[dict[str, Any]]) -> Optional[list[str]]:
    """Containers whose compose `depends_on` label names this container's service.

    Returns None when no container carries a depends_on label (dependents unknown).
    """
    service = (summary.get("Labels") or {}).get("com.docker.compose.service")
    any_label = False
    out: list[str] = []
    for other in summaries:
        dep = (other.get("Labels") or {}).get("com.docker.compose.depends_on")
        if dep is None:
            continue
        any_label = True
        wanted = {part.split(":", 1)[0] for part in dep.split(",") if part}
        if service and service in wanted and _name(other) != _name(summary):
            out.append(_name(other))
    if not any_label:
        return None
    return sorted(out)[:_MAX_DEPENDENTS]


def rank_key(candidate: dict[str, Any]) -> tuple[int, str]:
    return (_RANK.get(candidate["reason"], 9), candidate["container"])


async def gather_candidates(
    summaries: list[dict[str, Any]],
    get_detail: Callable[[str], Awaitable[Optional[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    pre = []
    for s in summaries:
        reason = reason_from_summary(s)
        if reason is not None:
            pre.append((s, reason))
    pre.sort(key=lambda t: _name(t[0]))
    out: list[dict[str, Any]] = []
    looked_up = 0
    for s, reason in pre:
        detail = None
        if looked_up < MAX_DETAIL:
            detail = await get_detail(s.get("Id", ""))
            looked_up += 1
        if reason == "needs_detail":
            if not ((detail or {}).get("State") or {}).get("OOMKilled"):
                continue  # SIGKILL without an OOM signature = stopped on purpose
            reason = "crashed"
        name = _name(s)
        out.append(
            {
                "container": name,
                "state": s.get("State"),
                "reason": reason,
                "evidence": build_evidence(s, detail),
                "eligibility": classify(name, s.get("Labels") or {}).as_dict(),
                "dependents": dependents_of(s, summaries),
            }
        )
    out.sort(key=rank_key)
    return out


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def evidence_digest(evidence: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(evidence).encode()).hexdigest()


def build_plan(candidate: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "version": PLAN_VERSION,
        "action": "restart",
        "target": candidate["container"],
        "reason": candidate["reason"],
        "evidence_digest": evidence_digest(candidate["evidence"]),
        "run_id": run_id,
    }


def plan_hash(plan: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(plan).encode()).hexdigest()


def build_report(candidates: list[dict[str, Any]], run_id: str, notes: list[str]) -> dict[str, Any]:
    eligible = [c for c in candidates if c["eligibility"]["allowed"]]
    proposal = None
    if eligible:
        plan = build_plan(eligible[0], run_id)
        proposal = {
            "plan": plan,
            "plan_hash": plan_hash(plan),
            "summary": f"restart {plan['target']}: {plan['reason']}",
        }
    return {
        "ok": True,
        "has_proposal": proposal is not None,
        "proposal": proposal,
        "candidates": candidates,
        "not_eligible": [
            f"{c['container']}: {c['eligibility']['blocked_by']}"
            for c in candidates
            if not c["eligibility"]["allowed"]
        ],
        "notes": notes,
    }
