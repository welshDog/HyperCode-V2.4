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
    depends_on: frozenset = frozenset()
    env_var_names: frozenset = frozenset()


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


def _depends_on_names(cfg) -> frozenset:
    """compose `depends_on:` may be a list of names or a dict of
    name -> {condition: ...}; either way we only need the names."""
    dep = cfg.get("depends_on")
    if not dep:
        return frozenset()
    if isinstance(dep, dict):
        return frozenset(dep.keys())
    return frozenset(str(d) for d in dep)


def _env_var_names(cfg) -> frozenset:
    """compose `environment:` may be a dict ({KEY: value}) or a list
    ("KEY=value" or bare "KEY" strings); either way we only need the
    variable *names* being referenced, never their values."""
    env = cfg.get("environment")
    if not env:
        return frozenset()
    if isinstance(env, dict):
        return frozenset(env.keys())
    return frozenset(str(item).split("=", 1)[0] for item in env)


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
                depends_on=_depends_on_names(cfg),
                env_var_names=_env_var_names(cfg),
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


CORE_FILE = "docker-compose.core.yml"
GRAPH_FILES = FILES + [CORE_FILE]

# Shared-resource env vars -> the service they imply a dependency on. Not
# general network/volume inference (too noisy — nearly everything shares
# agents-net for routing without depending on each other); this is a
# small, reviewable list of the exact variable names this repo's compose
# files use to reach shared infra, standardized in the
# POSTGRES_HOST/REDIS_HOST indirection work (2026-08-23).
_SHARED_RESOURCE_ENV_VARS = {
    "POSTGRES_HOST": "postgres",
    "DATABASE_URL": "postgres",
    "POSTGRES_URL": "postgres",
    "HYPERCODE_DB_URL": "postgres",
    "REDIS_HOST": "redis",
    "REDIS_URL": "redis",
    "CORE_URL": "hypercode-core",
}


def build_edges(registry: FleetRegistry) -> dict:
    """service name -> frozenset of service names it depends on (compose
    depends_on union env-var-inferred). Pure function of the registry;
    never cached, matching this module's own convention."""
    edges = {}
    for name, svc in registry.services.items():
        targets = set(svc.depends_on)
        for env_name in svc.env_var_names:
            target = _SHARED_RESOURCE_ENV_VARS.get(env_name)
            if target:
                targets.add(target)
        edges[name] = frozenset(targets)
    return edges


@dataclass(frozen=True)
class ImpactResult:
    profile: str
    upstream: frozenset
    downstream_already_running: frozenset


def impact_set(registry: FleetRegistry, profile: str) -> ImpactResult:
    """What a profile's services need upstream (transitive), and what
    already-running (no-profile) services depend on them downstream
    (direct). A profile matching zero services returns empty sets, not an
    error — that's a legitimate (if suspicious) result for the caller to
    display, not a registry failure."""
    edges = build_edges(registry)
    profile_services = {
        name for name, svc in registry.services.items() if profile in svc.profiles
    }

    upstream = set()
    frontier = set(profile_services)
    while frontier:
        next_frontier = set()
        for name in frontier:
            for dep in edges.get(name, frozenset()):
                if dep not in upstream and dep not in profile_services:
                    upstream.add(dep)
                    next_frontier.add(dep)
        frontier = next_frontier

    downstream_already_running = set()
    for name, svc in registry.services.items():
        if svc.profiles:
            continue
        if edges.get(name, frozenset()) & profile_services:
            downstream_already_running.add(name)

    return ImpactResult(
        profile=profile,
        upstream=frozenset(upstream),
        downstream_already_running=frozenset(downstream_already_running),
    )
