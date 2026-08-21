#!/usr/bin/env python3
"""Fail if two fleet services publish the same host port without an
explicit, reviewed exception.

Collisions are derived live from the real compose files by
fleet_registry.py; the intentional-collision allowlist lives in
.github/scripts/fleet_overlay.yml.
See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.

Used by both .github/workflows/health-check.yml and
.github/workflows/ghost-agents-build.yml — single source of truth so the
two gates can't drift out of sync with each other.
"""
import sys

from fleet_registry import RegistryError, build


def main():
    try:
        registry = build()
    except RegistryError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    ports_to_services = {}
    for svc in registry.services.values():
        if svc.host_port:
            ports_to_services.setdefault(svc.host_port, []).append(svc.name)

    errors = []
    for port, names in sorted(ports_to_services.items()):
        if len(names) <= 1:
            continue
        allowed = registry.allowed_collisions.get(port)
        if allowed and set(names) <= allowed:
            continue
        for name in sorted(names):
            source = registry.services[name].source_file
            errors.append(f"{port}: {name} ({source})")

    if errors:
        print("DUPLICATE HOST PORTS FOUND:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    total = sum(len(v) for v in ports_to_services.values())
    print(
        f"PASS: no unexpected duplicate host ports across {total} port "
        f"mappings ({len(ports_to_services)} distinct ports)."
    )


if __name__ == "__main__":
    main()
