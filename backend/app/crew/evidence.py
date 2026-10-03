"""Evidence bundle: hashes that pin what the crew produced, never the content itself.

The content lives in the run's history (already persisted and redacted). A bundle carries
pointers + sha256 so a later reader can prove nothing was changed after the guard decided.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.crew.baton import MAX_EVIDENCE, Evidence, EvidenceKind


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def node_ref(run_id: str, node: str) -> str:
    return f"run:{run_id}:node:{node}"


def evidence_for(kind: EvidenceKind, run_id: str, node: str, content: str) -> Evidence:
    """Evidence pointing at a node's output; ``content`` must already be redacted."""
    return Evidence(kind=kind, ref=node_ref(run_id, node), sha256=sha256_hex(content))


def build_bundle(run_id: str, plan_hash: str, items: list[Evidence]) -> dict[str, Any]:
    if len(items) > MAX_EVIDENCE:
        raise ValueError(f"an evidence bundle holds at most {MAX_EVIDENCE} items")
    body = {
        "run_id": run_id,
        "plan_hash": plan_hash,
        "evidence": [e.model_dump() for e in items],
    }
    return {**body, "bundle_hash": "sha256:" + sha256_hex(canonical_json(body))}


def verify_bundle(bundle: dict[str, Any]) -> bool:
    """True only if the bundle hash matches its own contents."""
    try:
        body = {k: bundle[k] for k in ("run_id", "plan_hash", "evidence")}
        return bool(bundle["bundle_hash"] == "sha256:" + sha256_hex(canonical_json(body)))
    except (KeyError, TypeError):
        return False
