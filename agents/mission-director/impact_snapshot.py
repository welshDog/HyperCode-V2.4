# agents/mission-director/impact_snapshot.py
"""
Computes the advisory ImpactView list attached to a MissionProposal --
what a proposed plan's profile(s) need upstream, and what already-running
(no-profile) services depend on them downstream. Purely advisory: unlike
truth_snapshot.py, a failure here never aborts the propose call -- it
degrades to one ImpactView(available=False, reason=...) entry per
requested profile. See
docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md.

Same bind-mount, same "never cache, compute fresh" rule as truth_snapshot.py.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/truth")

from fleet_registry import GRAPH_FILES, RegistryError, build, impact_set  # noqa: E402

from models import ImpactView

_MOUNT_DIR = "/app/truth"
_OVERLAY = f"{_MOUNT_DIR}/fleet_overlay.yml"


def _graph_files() -> list[str]:
    return [f"{_MOUNT_DIR}/{f}" for f in GRAPH_FILES]


def get_impact(
    profiles: list[str],
    files: list[str] | None = None,
    overlay_path: str | None = None,
) -> list[ImpactView]:
    views: list[ImpactView] = []
    for profile in profiles:
        try:
            registry = build(
                files=files if files is not None else _graph_files(),
                overlay_path=overlay_path or _OVERLAY,
            )
            result = impact_set(registry, profile)
        except (RegistryError, FileNotFoundError) as exc:
            views.append(ImpactView(profile=profile, available=False, reason=str(exc)))
            continue
        views.append(
            ImpactView(
                profile=profile,
                upstream=sorted(result.upstream),
                downstream_already_running=sorted(result.downstream_already_running),
                available=True,
            )
        )
    return views
