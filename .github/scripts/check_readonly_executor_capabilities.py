#!/usr/bin/env python3
"""Prove every "read_only" claim in the dispatch capability registry.

``agents/crew-orchestrator/dispatch_capability.json`` (card d's registry) lets
the orchestrator route a dispatch to <agent> down the fail-OPEN path when that
agent is marked ``"read_only"``. That is a *claim*. This is the proof: for
every agent the registry marks ``"read_only"``, its compose service must carry

  * no ``/var/run/docker.sock`` mount and no ``DOCKER_HOST``
  * no credential env var — ``*_TOKEN``, ``KUBECONFIG``, ``AWS_* / GCP_* /
    AZURE_* / STRIPE_* / DEPLOY_*``, or a key containing ``SECRET`` /
    ``PRIVATE_KEY`` (checked in ``environment`` and in any ``env_file``)
  * no writable host bind mount (a bind mount without a ``:ro`` suffix)

Any registry key — ``"read_only"`` or ``"mutation"`` — whose compose service
can't be found is a failure, not a skip: a ``read_only`` claim you cannot prove
is a false claim, and a phantom ``mutation`` key is roster drift that would
otherwise hide behind card (d)'s deny-first default.

LIMITATIONS — this reads the *committed* manifests statically (``yaml.safe_load``).
It does NOT run ``docker compose config``, so YAML anchors / merge keys,
``extends``, and ``${VAR}`` interpolation are not expanded. ``_PASSWORD`` env
vars are deliberately not flagged (a read-only agent may legitimately hold a DB
*read* password). An ``env_file`` that cannot be read (e.g. a gitignored
``.env`` absent in CI) is reported as a violation for a read_only agent — an
unprovable claim is treated as a failed one, so a read_only agent must inline
its environment or ship a committed env file. A PASS means "no grant visible in
the committed compose files", not a full runtime proof.

Companion to ``agents/crew-orchestrator/dispatch_capability.py``. Exit 0 =
every read_only claim is clean; exit 1 = at least one claim is unproven or false.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REGISTRY = _REPO_ROOT / "agents" / "crew-orchestrator" / "dispatch_capability.json"

try:  # keep the compose-file list in one place
    from fleet_registry import FILES as _FLEET_FILES

    _DEFAULT_COMPOSE = [str(_REPO_ROOT / f) for f in _FLEET_FILES]
except Exception:  # pragma: no cover - fallback if fleet_registry moves
    _DEFAULT_COMPOSE = [
        str(_REPO_ROOT / "docker-compose.agents.yml"),
        str(_REPO_ROOT / "docker-compose.agents-full.yml"),
        str(_REPO_ROOT / "docker-compose.bropets.yml"),
        str(_REPO_ROOT / "docker-compose.brain.yml"),
    ]

READ_ONLY = "read_only"

_FORBIDDEN_ENV_EXACT = {"DOCKER_HOST", "KUBECONFIG"}
_FORBIDDEN_ENV_PREFIX = ("AWS_", "GCP_", "AZURE_", "STRIPE_", "DEPLOY_", "GH_")
_FORBIDDEN_ENV_SUBSTR = ("SECRET", "PRIVATE_KEY")


class CheckError(Exception):
    """The check cannot be completed — a claim is unprovable (missing registry,
    unparseable registry, or a read_only agent with no compose service)."""


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def _load_registry(path: str) -> dict:
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CheckError(f"registry not found: {p}") from exc
    except (OSError, ValueError) as exc:
        raise CheckError(f"registry unreadable ({p}): {exc}") from exc
    if not isinstance(raw, dict):
        raise CheckError(f"registry is not a JSON object: {p}")
    return raw


def _load_services(compose_files) -> dict:
    """Merge ``services`` across every compose file that exists. Later files win."""
    merged: dict = {}
    for fn in compose_files:
        p = Path(fn)
        if not p.exists():
            continue
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for name, svc in (doc.get("services") or {}).items():
            merged[name] = (svc or {}, str(p))
    return merged


def _resolve_service(agent: str, services: dict):
    for key in (agent, agent.replace("-", "_"), agent.replace("_", "-")):
        if key in services:
            return key, services[key]
    return None, (None, None)


# --------------------------------------------------------------------------- #
# grant detection
# --------------------------------------------------------------------------- #
def _env_items(svc: dict):
    env = svc.get("environment") or {}
    if isinstance(env, dict):
        return list(env.keys())
    return [str(e).split("=", 1)[0].strip() for e in env]


def _env_file_keys(svc: dict, source_file: str):
    """Return (keys, unresolved) — env var names from every resolvable env_file,
    plus the list of env_file targets that could not be read. An unresolvable
    env_file on a read_only agent is an unprovable claim, so the caller treats
    ``unresolved`` as violations (same doctrine as service-not-found)."""
    keys: list[str] = []
    unresolved: list[str] = []
    ef = svc.get("env_file") or []
    if isinstance(ef, str):
        ef = [ef]
    base = Path(source_file).resolve().parent
    for rel in ef:
        target = (base / str(rel)).resolve()
        if not target.exists():
            unresolved.append(str(rel))
            continue
        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                keys.append(line.split("=", 1)[0].strip())
    return keys, unresolved


def _forbidden_env(key: str) -> bool:
    k = key.upper()
    if k in _FORBIDDEN_ENV_EXACT:
        return True
    if k.endswith("_TOKEN"):
        return True
    if any(k.startswith(pfx) for pfx in _FORBIDDEN_ENV_PREFIX):
        return True
    return any(sub in k for sub in _FORBIDDEN_ENV_SUBSTR)


def _writable_host_mount(vol) -> str | None:
    if isinstance(vol, dict):
        if vol.get("type") == "bind" and vol.get("read_only") is not True:
            return f"{vol.get('source')} -> {vol.get('target')}"
        return None
    s = str(vol)
    parts = s.split(":")
    if len(parts) < 2:
        return None  # anonymous / named-only
    host, mode = parts[0], (parts[2] if len(parts) > 2 else "")
    is_bind = host.startswith((".", "/", "~", "$")) or "/" in host
    if is_bind and mode != "ro":
        return s
    return None


def _service_violations(agent: str, svc: dict, source_file: str) -> list[str]:
    out: list[str] = []

    for vol in svc.get("volumes") or []:
        if "docker.sock" in str(vol):
            out.append(f"{agent}: docker.sock mounted ({vol}) [{os.path.basename(source_file)}]")
            continue
        wm = _writable_host_mount(vol)
        if wm:
            out.append(
                f"{agent}: writable host bind mount ({wm}) [{os.path.basename(source_file)}]"
            )

    env_file_keys, unresolved = _env_file_keys(svc, source_file)
    for rel in unresolved:
        out.append(
            f"{agent}: env_file {rel!r} could not be read — cannot prove it holds "
            f"no credentials [{os.path.basename(source_file)}]"
        )
    for key in _env_items(svc) + env_file_keys:
        if _forbidden_env(key):
            out.append(
                f"{agent}: credential env var {key} [{os.path.basename(source_file)}]"
            )

    return out


# --------------------------------------------------------------------------- #
# top level
# --------------------------------------------------------------------------- #
def collect_violations(registry_path: str, compose_files) -> list[str]:
    registry = _load_registry(registry_path)
    services = _load_services(compose_files)
    basenames = [os.path.basename(f) for f in compose_files]

    # Roster-drift guard: EVERY registry key must resolve to a real compose
    # service, whatever its capability. A typo'd key would otherwise be silent
    # — deny-first would classify it "mutation" (fail-safe), but the roster
    # drift would hide. Fail visibly instead.
    unknown = sorted(
        a for a in registry if _resolve_service(a, services)[0] is None
    )
    if unknown:
        raise CheckError(
            f"registry key(s) with no compose service in {basenames}: "
            f"{', '.join(unknown)}"
        )

    read_only = sorted(a for a, cap in registry.items() if cap == READ_ONLY)
    violations: list[str] = []
    for agent in read_only:
        _name, (svc, source) = _resolve_service(agent, services)
        violations.extend(_service_violations(agent, svc, source))
    return violations


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(_DEFAULT_REGISTRY))
    ap.add_argument(
        "--compose",
        action="append",
        default=None,
        help="compose file (repeatable); defaults to the fleet compose set",
    )
    args = ap.parse_args(argv)
    compose_files = args.compose or _DEFAULT_COMPOSE

    try:
        violations = collect_violations(args.registry, compose_files)
    except CheckError as exc:
        print(f"FAIL: {exc}")
        return 1

    if violations:
        print("FAIL: read_only executor(s) hold mutation-capable grants:")
        for v in violations:
            print(f"  {v}")
        return 1

    print(
        "PASS: every registry key resolves to a compose service and every "
        "read_only executor is grant-clean."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
