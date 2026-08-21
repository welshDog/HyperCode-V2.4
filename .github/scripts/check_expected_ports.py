#!/usr/bin/env python3
"""Fail if any of the 26-agent fleet roster's ports isn't declared in compose.

Full canonical port registry (2026-08-21). 13 of these (project-strategist
through hyper-worker below) are defined ONLY in docker-compose.agents.yml —
their duplicate blocks were deleted from docker-compose.agents-full.yml
2026-08-20 late evening, which now owns just the remaining 12 (security-engineer
through fleet-controller below). This dict intentionally tracks all 26
regardless of which file defines each one — docker-compose.yml itself is an
`include:` wrapper with no services of its own, so it's never read here.
hypercode-mcp-server (:8823, the real live core service, not a ghost agent)
stays deliberately omitted — see docs/NEXT_TASKS.md.
"""
import sys

import yaml

EXPECTED_PORTS = {
    "8001": "project-strategist",
    "8002": "coder-agent",
    "8003": "backend-specialist",
    "8004": "database-architect",
    "8005": "qa-engineer",
    "8006": "devops-engineer",
    "8007": "security-engineer",
    "8010": "system-architect",
    "8012": "frontend-specialist",
    "8013": "hyper-split-agent",
    "8014": "throttle-agent",
    "8015": "super-hyper-broski-agent",
    "8017": "session-snapshot",
    "8018": "tips-tricks-writer",
    "8019": "test-agent",
    "8020": "business-agent",
    "8024": "coderabbit-webhook",
    "8050": "goal-keeper",
    "8081": "crew-orchestrator",
    "8082": "brain-agent",
    "8084": "agent-x",
    "8091": "hyper-architect",
    "8092": "hyper-observer",
    "8093": "hyper-worker",
    "8094": "fleet-controller",
}

FILES = ["docker-compose.agents.yml", "docker-compose.agents-full.yml"]


def host_port(mapping):
    parts = str(mapping).split(":")
    return parts[-2] if len(parts) >= 2 else parts[0]


def main():
    found_ports = set()
    for fname in FILES:
        try:
            with open(fname, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except FileNotFoundError:
            continue
        for svc, cfg in (doc.get("services") or {}).items():
            for p in (cfg or {}).get("ports", []):
                found_ports.add(host_port(p))

    missing = [
        f"  MISSING: :{port} ({name})"
        for port, name in EXPECTED_PORTS.items()
        if port not in found_ports
    ]

    if missing:
        print("FAIL: Some agent ports not declared in compose files:")
        for m in missing:
            print(m)
        sys.exit(1)

    print(f"PASS: All {len(EXPECTED_PORTS)} agent ports confirmed in compose files.")


if __name__ == "__main__":
    main()
