"""Deny-first executor capability classification — the dispatch routing seam.

This module answers exactly one question: when the orchestrator dispatches a
task to <agent>, must that dispatch cross the strict, fail-closed mutation
client, or may it use the availability-first (fail-open) path?

    classify("qa-engineer")     -> "read_only"   (only if explicitly registered)
    classify("coder-studio")    -> "mutation"
    classify("brand-new-agent") -> "mutation"    (unregistered => deny-first)

Invariants — do NOT weaken without a security review:

  * Unknown / unregistered agent                     -> "mutation"
  * Missing, unreadable, or non-object registry file -> every agent "mutation"
    (logged at ERROR — a silent empty registry must still fail safe)
  * Any registry value that is not exactly "read_only" -> "mutation"
  * There is NO caller-supplied override. Classification comes only from the
    reviewed registry file. Narrowing a mutation-capable executor to read-only
    work per-task is a future feature and needs its own proof obligation.

A companion check (not here) must prove every agent listed "read_only" has a
rendered container config with no mutation grants (docker.sock, DOCKER_HOST,
GITHUB_TOKEN, deploy / payment credentials). Listing an agent read_only is a
claim; that check is the proof.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

READ_ONLY = "read_only"
MUTATION = "mutation"

_DEFAULT_REGISTRY_PATH = os.getenv(
    "DISPATCH_CAPABILITY_REGISTRY",
    str(Path(__file__).with_name("dispatch_capability.json")),
)


def load_registry(path: "str | os.PathLike[str] | None" = None) -> dict[str, str]:
    """Return a clean ``{agent_name: "read_only" | "mutation"}`` map.

    Every failure to produce a well-formed dict returns ``{}`` — which, via
    :func:`classify`'s default, means every agent is treated as
    mutation-capable. Failures are logged at ERROR, never swallowed silently.
    """
    p = Path(path or _DEFAULT_REGISTRY_PATH)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.error(
            "dispatch capability registry not found at %s; "
            "treating ALL executors as mutation-capable",
            p,
        )
        return {}
    except (OSError, ValueError) as exc:
        logger.error(
            "dispatch capability registry at %s is unreadable (%s); "
            "treating ALL executors as mutation-capable",
            p,
            exc,
        )
        return {}

    if not isinstance(raw, dict):
        logger.error(
            "dispatch capability registry at %s is not a JSON object; "
            "treating ALL executors as mutation-capable",
            p,
        )
        return {}

    clean: dict[str, str] = {}
    for name, cap in raw.items():
        if cap == READ_ONLY:
            clean[str(name)] = READ_ONLY
        else:
            if cap != MUTATION:
                logger.warning(
                    "registry entry %r has unrecognised capability %r; "
                    "treating as mutation",
                    name,
                    cap,
                )
            clean[str(name)] = MUTATION
    return clean


def classify(agent_name: str, registry: "dict[str, str] | None" = None) -> str:
    """Return :data:`READ_ONLY` only for an agent explicitly registered so.

    Everything else — unregistered, blank name, or a registry value that is
    not exactly ``"read_only"`` — is :data:`MUTATION`.
    """
    if registry is None:
        registry = load_registry()
    if not agent_name:
        return MUTATION
    return READ_ONLY if registry.get(agent_name) == READ_ONLY else MUTATION


def needs_strict_path(agent_name: str, registry: "dict[str, str] | None" = None) -> bool:
    """True when this dispatch MUST cross the fail-closed mutation client."""
    return classify(agent_name, registry) == MUTATION
