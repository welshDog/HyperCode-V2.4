#!/usr/bin/env python3
"""Fail if fleet-controller's compose manifest grants any mutation authority.

fleet-controller (Phase 0 of the mission-director/fleet-controller
architecture) is designed to be structurally incapable of executing
anything: no Docker socket, no DOCKER_HOST, no crew-orchestrator credential,
no LLM client. This is the negative-capability proof — see
docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md.
"""
import sys

import yaml


def main():
    with open("docker-compose.agents-full.yml", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    svc = (doc.get("services") or {}).get("fleet-controller")
    if svc is None:
        print("FAIL: fleet-controller service not found in docker-compose.agents-full.yml")
        sys.exit(1)

    errors = []

    for vol in svc.get("volumes") or []:
        if "docker.sock" in str(vol):
            errors.append(f"docker.sock mounted: {vol}")

    env = svc.get("environment") or []
    env_text = " ".join(env) if isinstance(env, list) else " ".join(f"{k}={v}" for k, v in env.items())
    for forbidden in ("DOCKER_HOST", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "ORCHESTRATOR_API_KEY"):
        if forbidden in env_text:
            errors.append(f"forbidden env var present: {forbidden}")

    depends_on = svc.get("depends_on") or {}
    if "crew-orchestrator" in depends_on:
        errors.append(
            "depends_on crew-orchestrator — fleet-controller should have no "
            "dispatch-path dependency in Phase 0"
        )

    if errors:
        print("FAIL: fleet-controller manifest grants excess capability:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    print(
        "PASS: fleet-controller has no docker.sock, no forbidden env vars, "
        "no crew-orchestrator dependency."
    )


if __name__ == "__main__":
    main()
