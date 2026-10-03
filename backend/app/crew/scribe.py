"""Scribe: drafts the handover for a finished crew run as a PROPOSAL. It never writes anywhere.

What it produces is plain data: one handover file and one WHATS_DONE entry, a draft-PR title/body, and a
hash of all of it. A human reads exactly that, approves with exactly that hash (same pattern as the plan
gate), and only then may the publisher open a *draft* PR. Deterministic: no LLM, no network, no clock
inside the drafting itself (the date is passed in), and everything comes from the run's own redacted,
hash-pinned history. It states only what the run can prove, and says plainly what it did not do.

Why a separate proposals file for the WHATS_DONE entry instead of editing ``WHATS_DONE.md``: that file is
edited in parallel by other sessions, and a whole-file replace from here could silently clobber their work.
A new file under ``docs/crew-proposals/`` can only ever be created, never overwrite anything.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from app.broski_operator.recover_tools import _last_data, _last_result
from app.crew.evidence import canonical_json, sha256_hex
from app.crew.quests import evaluate
from app.crew.redaction import redact_text

HANDOVER_PREFIX = "docs/NEXT_SESSION_HANDOVER_"
PROPOSALS_PREFIX = "docs/crew-proposals/"
ALLOWED_PREFIXES = (HANDOVER_PREFIX, PROPOSALS_PREFIX)
MAX_FILE_BYTES = 32_000
MAX_SNIPPET = 600
SCRIBE_NODE = "scribe"
GATE_NODE = "approve_scribe"

_PATH_OK = re.compile(r"^[A-Za-z0-9_./-]+\.md$")


class ScribeError(RuntimeError):
    """The run cannot honestly be written up (or the approval does not match the draft)."""


def path_allowed(path: str) -> bool:
    """Docs only, markdown only, no traversal. The publisher refuses anything else."""
    return (
        isinstance(path, str)
        and bool(_PATH_OK.match(path))
        and ".." not in path.split("/")
        and not path.startswith("/")
        and path.startswith(ALLOWED_PREFIXES)
    )


def proposal_hash(proposal: dict[str, Any]) -> str:
    """Hash of everything a human approves. ``plan_hash`` is excluded: it IS this value."""
    body = {k: v for k, v in proposal.items() if k != "plan_hash"}
    return "sha256:" + sha256_hex(canonical_json(body))


def _snippet(text: Any) -> str:
    one = " ".join(redact_text(str(text or "")).split())
    return one[:MAX_SNIPPET] + ("…" if len(one) > MAX_SNIPPET else "")


def _handover_text(run_id: str, day: date, goal: str, plan_hash: str, build: str, verify: str,
                   checks: list[dict[str, Any]], bundle_hash: str) -> str:
    rows = "\n".join(
        f"| {c.get('name', '?')} | {'PASS' if c.get('passed') else 'FAIL'} | {_snippet(c.get('detail')).replace('|', '/')} |"
        for c in checks[:12] if isinstance(c, dict)
    )
    return f"""# 📋 NEXT_SESSION_HANDOVER — {day.isoformat()} (HyperCrew run {run_id[:8]})

> Drafted by the HyperCrew Scribe from this run's own evidence. Nothing here was written to the repo until a
> human approved this exact text. Treat it as a draft: edit it freely.

---

## 🟢 LIVE STATE RIGHT NOW

- Run `{run_id}` finished and the Guardian said **ALLOW**.
- The crew only **proposed** a change as text. **Nothing was applied, built, deployed or restarted.**
- Goal: {_snippet(goal)}

## ✅ PROOF

| Check | Result | Detail |
|---|---|---|
{rows}

- Approved plan hash: `{plan_hash}`
- Evidence bundle: `{bundle_hash}`

## 🛠️ WHAT THE CREW PROPOSED

- Builder: {_snippet(build)}
- Verifier: {_snippet(verify)}

## ⚠️ NOT DONE / NOT PROVEN

- The proposed change has **not** been applied to any file. Someone has to read it and decide.
- Anything the verifier could only judge from text was not run for real.

## ▶️ NEXT TASK

Read the proposed change for run `{run_id[:8]}` and decide: apply it by hand, or drop it.
"""


def _whats_done_text(run_id: str, day: date, goal: str, bundle_hash: str) -> str:
    return f"""## {day.isoformat()} — HyperCrew run {run_id[:8]}: a proposed change passed the Guardian

- Goal: {_snippet(goal)}
- The Guardian allowed it with an evidence bundle (`{bundle_hash}`).
- **Proposal only:** nothing was applied or deployed by the crew.
- Not done: applying the change; a human has to read it first.

(Paste this under the top of `WHATS_DONE.md` when you apply the change. Drafted, not merged.)
"""


def build_proposal(run_id: str, history: list[dict[str, Any]], day: date) -> dict[str, Any]:
    """Draft the write-up. Raises ``ScribeError`` unless the run is one the Guardian allowed."""
    ev = evaluate(run_id, history)
    if not ev.eligible:
        raise ScribeError(f"nothing to write up: {ev.reason}")
    sealed = _last_data(history, "seal") or {}
    guard = _last_data(history, "guard") or {}
    plan: dict[str, Any] = sealed["plan"] if isinstance(sealed.get("plan"), dict) else {}
    goal = str(plan.get("goal", ""))
    build = str((_last_data(history, "build") or {}).get("summary", ""))
    verify = str((_last_data(history, "verify") or {}).get("summary", ""))
    checks: list[dict[str, Any]] = guard["checks"] if isinstance(guard.get("checks"), list) else []
    short = run_id[:8]
    handover_path = f"{HANDOVER_PREFIX}{day.isoformat()}_crew-{short}.md"
    entry_path = f"{PROPOSALS_PREFIX}{day.isoformat()}-{short}-whats-done-entry.md"
    files = [
        {"path": handover_path, "content": _handover_text(
            run_id, day, goal, str(sealed["plan_hash"]), build, verify, checks, ev.bundle_hash)},
        {"path": entry_path, "content": _whats_done_text(run_id, day, goal, ev.bundle_hash)},
    ]
    for f in files:
        if not path_allowed(f["path"]) or len(f["content"].encode("utf-8")) > MAX_FILE_BYTES:
            raise ScribeError("draft is outside what the Scribe may propose")
        f["sha256"] = sha256_hex(f["content"])
    proposal: dict[str, Any] = {
        "kind": "crew.handover.proposal",
        "run_id": run_id,
        "files": files,
        "pr": {
            "title": f"docs: HyperCrew handover for run {short} (draft)",
            "branch": f"crew/handover-{day.isoformat()}-{short}",
            "draft": True,
            "body": (
                "Drafted by the HyperCrew Scribe after a human approved this exact text.\n\n"
                f"- Run: `{run_id}`\n- Guardian: ALLOW, evidence bundle `{ev.bundle_hash}`\n"
                "- Docs only. New files only. Nothing here changes code, and nothing was applied.\n"
            ),
        },
        "performed": False,
    }
    proposal["plan_hash"] = proposal_hash(proposal)
    return proposal


def approved_proposal(history: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    """The drafted proposal and the human who approved it, but only if that approval was for exactly it.

    Fails closed: any missing piece, any hash that does not match the recomputed one, any path outside
    the docs allow-list is a ``ScribeError``.
    """
    data = _last_data(history, SCRIBE_NODE) or {}
    proposal = data.get("proposal")
    if not isinstance(proposal, dict):
        raise ScribeError("no handover draft to publish")
    claimed = proposal.get("plan_hash")
    if not claimed or proposal_hash(proposal) != claimed:
        raise ScribeError("the draft does not match its hash")
    gate: Optional[dict[str, Any]] = _last_result(history, GATE_NODE)
    if not gate or gate.get("approved") is not True:
        raise ScribeError("the handover draft was not approved")
    if gate.get("plan_hash") != claimed:
        raise ScribeError("the approval was not for this exact draft")
    approver = gate.get("by")
    if not isinstance(approver, str) or not approver.strip():
        raise ScribeError("no recorded approver")
    files = proposal.get("files")
    if not isinstance(files, list) or not files or not all(
        isinstance(f, dict) and path_allowed(str(f.get("path"))) and isinstance(f.get("content"), str)
        and sha256_hex(f["content"]) == f.get("sha256") for f in files
    ):
        raise ScribeError("a file in the draft is not allowed or was changed")
    return proposal, approver.strip()
