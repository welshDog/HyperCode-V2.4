"""Local tool for `hypercode.recover` (Phase 2b): request a DRY_RUN capability from Governor.

Talks ONLY to Governor's real, already-live HTTP API — never to fleet-controller (its plan
schema is a closed set that deliberately excludes this action), never to Docker, never to
Safety Shepherd directly (Governor calls Shepherd internally as part of minting).

With today's policy configuration (no explicit capabilities.json grant for this caller),
Governor's mint always refuses via Shepherd's ESCALATE path, regardless of the requested mode.
That refusal is the correct, expected outcome this increment proves — not a tool failure.
Only a genuine failure to reach or parse Governor's response raises AuthorizeError.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.db.session import SessionLocal
from app.models.governance import GovernanceLedger

logger = logging.getLogger(__name__)

GOVERNOR_TIMEOUT_S = 8.0
_SEAL_NODE = "seal"


class AuthorizeError(RuntimeError):
    """A genuine failure to reach or interpret Governor's response. Never a policy refusal."""


def _governor_url() -> str:
    return (os.getenv("GOVERNOR_URL") or "http://governor:8080").rstrip("/")


def build_plan(run_id: str, target: str) -> dict[str, Any]:
    """The full Governor-shaped plan dict, with constraints spelled out explicitly.

    Governor's own `canonical_hash` operates on its Pydantic model's `model_dump(mode="json")`
    AFTER validation — which fills in `Constraints()`'s defaults. Omitting `constraints` here
    would make our client-side hash diverge from what Governor recomputes server-side. Spelling
    them out (matching `Constraints()`'s exact defaults) keeps the two hashes identical.
    """
    return {
        "schema_version": 1,
        "mission_id": run_id,
        "requested_actions": [
            {"action_id": f"restart-{target}", "kind": "container.restart", "profile": target}
        ],
        "constraints": {"max_services": 25, "allow_profiles": [], "deny_profiles": []},
    }


def canonical_hash(plan: dict[str, Any]) -> str:
    """sha256 over canonical JSON — the SAME algorithm as agents/governor/models.py:canonical_hash,
    reimplemented locally (file-copy convention: never import across the agent boundary).
    """
    import hashlib
    import json

    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _sealed_target(history: list[dict[str, Any]]) -> str:
    for entry in reversed(history):
        if entry.get("node") == _SEAL_NODE and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data") or {}
            plan = data.get("plan") or {}
            target = plan.get("target")
            if isinstance(target, str) and target:
                return target
    raise AuthorizeError("no sealed plan found in this run's history")


def _sealed_plan_hash(history: list[dict[str, Any]]) -> str:
    for entry in reversed(history):
        if entry.get("node") == _SEAL_NODE and entry.get("status") == "completed":
            data = (entry.get("result") or {}).get("data") or {}
            plan_hash = data.get("plan_hash")
            if isinstance(plan_hash, str) and plan_hash:
                return plan_hash
    raise AuthorizeError("no sealed plan_hash found in this run's history")


def _write_ledger(entry: dict[str, Any]) -> bool:
    try:
        db = SessionLocal()
        try:
            db.add(
                GovernanceLedger(
                    user_id="broski-operator",
                    action="recover_authorization_attempted",
                    tool_used="hypercode.recover",
                    payload=entry["payload"],
                    decision=entry["payload"]["governor_verdict"].get("decision"),
                    agent_name="broski-operator",
                    approved_by=None,
                )
            )
            db.commit()
            return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
        finally:
            db.close()
    except Exception:
        logger.warning("authorize: governance ledger insert failed", exc_info=True)
        return False


async def authorize(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    history = (ctx or {}).get("history", [])
    run_id = str((ctx or {}).get("run_id", ""))
    target = _sealed_target(history)
    plan_hash = _sealed_plan_hash(history)

    gov_plan = build_plan(run_id, target)
    governor_plan_hash = canonical_hash(gov_plan)
    body = {
        "plan": gov_plan,
        "plan_hash": governor_plan_hash,
        "mode": "DRY_RUN",
        "action": "container.restart",
        "target": target,
        "proposer_id": "broski-operator",
    }

    try:
        async with httpx.AsyncClient(timeout=GOVERNOR_TIMEOUT_S) as client:
            resp = await client.post(f"{_governor_url()}/v1/capabilities/mint", json=body)
    except Exception as exc:
        raise AuthorizeError(f"could not reach Governor: {type(exc).__name__}") from exc

    if resp.status_code != 200:
        raise AuthorizeError(f"Governor returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception as exc:
        raise AuthorizeError("Governor response was not valid JSON") from exc

    if not isinstance(data, dict) or "minted" not in data or "verdict" not in data:
        raise AuthorizeError("Governor response missing required fields")

    verdict = data.get("verdict") or {}
    minted = bool(data.get("minted"))
    ledger_ok = _write_ledger(
        {
            "payload": {
                "run_id": run_id,
                "plan_hash": plan_hash,
                "governor_plan_hash": governor_plan_hash,
                "governor_verdict": verdict,
                "minted": minted,
                "mode": "DRY_RUN",
            }
        }
    )

    return {
        "ok": True,
        "minted": minted,
        "mode": "DRY_RUN",
        "verdict": verdict,
        "plan_hash": plan_hash,
        "governor_plan_hash": governor_plan_hash,
        "ledger": ledger_ok,
        "note": (
            "Governor/Shepherd correctly refused — no capability minted, no second approver "
            "on record; this increment proves the pipeline, not a minted capability"
            if not minted
            else "capability minted (unexpected for this increment's default policy configuration)"
        ),
    }
