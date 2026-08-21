#!/usr/bin/env python3
"""Single source of truth for the 26-agent fleet.

Parses ports/context/profiles live from the real compose files and merges
in a thin overlay (fleet_overlay.yml) for the handful of facts compose
can't express: which services count as "the fleet roster", and which port
collisions are genuinely intentional. Never writes a generated snapshot to
disk — always computed fresh from the compose files at call time.

See docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

FILES = [
    "docker-compose.agents.yml",
    "docker-compose.agents-full.yml",
    "docker-compose.bropets.yml",
    "docker-compose.brain.yml",
]

_OVERLAY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet_overlay.yml")


class RegistryError(Exception):
    """The overlay is syntactically fine but semantically stale: a roster
    entry or allowed-collision pair no longer matches the real compose
    files."""


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    host_port: str
    container_port: str
    source_file: str
    profiles: frozenset


@dataclass(frozen=True)
class FleetRegistry:
    services: dict
    roster: frozenset
    allowed_collisions: dict


def _host_port(mapping) -> str:
    """'HOST:CONTAINER' or 'BIND_IP:HOST:CONTAINER' -> the host port field."""
    parts = str(mapping).split(":")
    return parts[-2] if len(parts) >= 2 else parts[0]


def _container_port(mapping) -> str:
    return str(mapping).split(":")[-1]


def _parse_compose_files(files):
    services = {}
    for fname in files:
        try:
            with open(fname, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except FileNotFoundError:
            continue
        for svc, cfg in (doc.get("services") or {}).items():
            cfg = cfg or {}
            ports = cfg.get("ports") or []
            profiles = frozenset(cfg.get("profiles") or [])
            if len(ports) > 1:
                raise RegistryError(
                    f"service {svc!r} in {fname} publishes {len(ports)} ports "
                    f"({ports}) — fleet_registry.py only tracks one port per "
                    f"service; extend ServiceInfo before adding a multi-port "
                    f"fleet service"
                )
            host_port = _host_port(ports[0]) if ports else ""
            container_port = _container_port(ports[0]) if ports else ""
            services[svc] = ServiceInfo(
                name=svc,
                host_port=host_port,
                container_port=container_port,
                source_file=fname,
                profiles=profiles,
            )
    return services


def _load_overlay(path):
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    roster = frozenset(doc.get("roster") or [])
    allowed_collisions = {
        str(port): frozenset(names)
        for port, names in (doc.get("allowed_collisions") or {}).items()
    }
    return roster, allowed_collisions


def build(files: Optional[list] = None, overlay_path: Optional[str] = None) -> FleetRegistry:
    """Parse the fleet compose files + the overlay, cross-validate, return
    the merged model. Raises RegistryError on any contract violation —
    never returns a silently-partial registry."""
    files = FILES if files is None else files
    overlay_path = _OVERLAY_FILE if overlay_path is None else overlay_path

    services = _parse_compose_files(files)
    roster, allowed_collisions = _load_overlay(overlay_path)

    missing_roster = sorted(name for name in roster if name not in services)
    if missing_roster:
        raise RegistryError(
            f"roster entry {missing_roster[0]!r} not found in any fleet "
            f"compose file (checked: {', '.join(files)})"
        )

    ports_by_host = {}
    for svc in services.values():
        if svc.host_port:
            ports_by_host.setdefault(svc.host_port, set()).add(svc.name)

    for port, overlay_names in allowed_collisions.items():
        real_names = ports_by_host.get(port, set())
        if len(real_names) < 2 or not overlay_names <= real_names:
            raise RegistryError(
                f"allowed_collisions[{port!r}] names {sorted(overlay_names)} "
                f"but compose has {sorted(real_names)} service(s) on that port"
            )

    return FleetRegistry(services=services, roster=roster, allowed_collisions=allowed_collisions)
