#!/usr/bin/env python3
"""Fail if two agent-fleet services publish the same host port.

Scans every compose layer that has ever actually defined a fleet agent or
collided with one — not just docker-compose.agents.yml/-full.yml. Real
historical collisions crossed both file AND profile boundaries
(session-snapshot :8097 vs evolve-relay, both literally profile "agents", in
docker-compose.bropets.yml; hyper-split-agent :8096 vs safety-shepherd in
docker-compose.agents.yml; test-agent :8100 vs hyper-brain in
docker-compose.brain.yml — all fixed 2026-08-20). Filtering by profile would
have hidden the first of those (same profile, different file); filtering to
just the two agent files would have hidden all three. So this scans every
file with an agent-fleet history, with no profile filter, and only excuses
the couple of pairs confirmed to be genuinely mutually-exclusive-by-
construction, not by profile assumption.

Deliberately excludes docker-compose.core.yml / observability.yml /
obsidian-sync.yml / grafana-cloud.yml — pure infra/monitoring layers outside
the agent-fleet roster this gate exists to protect. A real, separate
collision risk was found there while building this gate (hypercode-ollama
vs hypercode-ollama-gpu on :11434, prometheus vs prometheus-cloud on :9090 —
both currently safe only because their conflicting profiles have never been
combined) — logged in docs/NEXT_TASKS.md rather than folded in here, since
it's an infra-config decision, not an agent-port bug.

Used by both .github/workflows/health-check.yml and
.github/workflows/ghost-agents-build.yml — single source of truth so the two
gates can't drift out of sync with each other.
"""
import sys

import yaml

FILES = [
    "docker-compose.agents.yml",
    "docker-compose.agents-full.yml",
    "docker-compose.bropets.yml",
    "docker-compose.brain.yml",
]

# Genuinely intentional host-port reuse, confirmed by direct inspection
# (2026-08-21): a container can't hold two profiles' identity at once, so
# these pairs can never collide in a real running stack even though they
# share a host port on paper. Keyed by host port -> the exact service names
# allowed to share it — if a third, different service ever claims one of
# these ports, it still fails loudly.
ALLOWED_COLLISIONS = {
    # coder-agent (docker-compose.agents.yml, --profile agents) vs
    # ai-backend (docker-compose.agents.yml, --profile ai)
    "8002": {"coder-agent", "ai-backend"},
    # nemoclaw-agent (docker-compose.agents.yml, --profile agents/nemoclaw)
    # vs hyper-mission-ui (docker-compose.agents.yml, --profile mission)
    "8099": {"nemoclaw-agent", "hyper-mission-ui"},
}


def host_port(mapping):
    """'HOST:CONTAINER' or 'BIND_IP:HOST:CONTAINER' -> the host port field."""
    parts = str(mapping).split(":")
    return parts[-2] if len(parts) >= 2 else parts[0]


def main():
    owners = {}  # host_port -> {service_name: source_file}
    for fname in FILES:
        try:
            with open(fname, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except FileNotFoundError:
            continue
        for svc, cfg in (doc.get("services") or {}).items():
            for p in (cfg or {}).get("ports", []):
                port = host_port(p)
                owners.setdefault(port, {})[svc] = fname

    errors = []
    for port, services in sorted(owners.items()):
        if len(services) <= 1:
            continue
        allowed = ALLOWED_COLLISIONS.get(port)
        if allowed and set(services) <= allowed:
            continue
        for svc, fname in sorted(services.items()):
            errors.append(f"{port}: {svc} ({fname})")

    if errors:
        print("DUPLICATE HOST PORTS FOUND:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    total = sum(len(s) for s in owners.values())
    print(
        f"PASS: no unexpected duplicate host ports across {total} port "
        f"mappings ({len(owners)} distinct ports)."
    )


if __name__ == "__main__":
    main()
