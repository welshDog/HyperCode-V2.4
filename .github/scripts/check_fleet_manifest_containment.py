"""Assert the rendered compose manifest keeps fleet-controller and governor
inert: no docker.sock mount, no DOCKER_HOST, no crew-orchestrator credential.
The architecture is only real if the deployment manifest proves it.

Usage: check_fleet_manifest_containment.py <rendered-compose.yml>
"""
from __future__ import annotations

import sys

import yaml

WATCHED = ("fleet-controller", "governor")
BANNED_ENV = ("DOCKER_HOST", "ORCHESTRATOR_API_KEY", "CREW_ORCHESTRATOR_API_KEY")


def main(path: str) -> int:
    """Check the rendered compose manifest at `path` for containment
    violations on `WATCHED` services; print each failure and return 1,
    or 0 if none found.
    """
    doc = yaml.safe_load(open(path)) or {}
    services = doc.get("services", {}) or {}
    failures: list[str] = []

    for name in WATCHED:
        svc = services.get(name)
        if not svc:
            failures.append(f"{name}: not present in the rendered manifest (expected)")
            continue
        for vol in svc.get("volumes", []) or []:
            if "docker.sock" in str(vol):
                failures.append(f"{name}: mounts docker.sock ({vol})")
        env = svc.get("environment", {}) or {}
        keys = env.keys() if isinstance(env, dict) else [e.split("=")[0] for e in env]
        for banned in BANNED_ENV:
            if banned in keys:
                failures.append(f"{name}: has banned env {banned}")

    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
