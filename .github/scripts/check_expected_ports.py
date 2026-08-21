#!/usr/bin/env python3
"""Fail if any fleet-roster agent isn't declared in compose.

Ports, contexts, and profiles are derived live from the real compose files
by fleet_registry.py — this script only asserts every roster name from
.github/scripts/fleet_overlay.yml resolves to a real service.
See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.
"""
import sys

from fleet_registry import RegistryError, build


def main():
    try:
        registry = build()
    except RegistryError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    missing = [n for n in sorted(registry.roster) if n not in registry.services]
    if missing:
        print("FAIL: roster names not found (should be impossible after build() validation):")
        for n in missing:
            print(f"  {n}")
        sys.exit(1)

    print(f"PASS: all {len(registry.roster)} roster agents confirmed in compose files.")


if __name__ == "__main__":
    main()
