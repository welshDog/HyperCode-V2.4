# agents/mission-director/truth_snapshot.py
"""
Produces the truth_snapshot_ref a MissionProposal is grounded against --
a deterministic hash of the live fleet registry, same canonical-hash
convention as models.canonical_hash (sorted-key, whitespace-free JSON,
sha256: prefix). Never caches: computed fresh on every call, matching
fleet_registry.py's own "never writes a generated snapshot to disk"
design note.

fleet_registry.py + fleet_overlay.yml + the 4 fleet compose files are
bind-mounted read-only into this container at /app/truth/ (wired in
docker-compose.agents-full.yml, Task 6) -- they are NOT baked into the
image, so the snapshot always reflects the live repo state, not a
build-time copy.
"""
from __future__ import annotations

import hashlib
import json
import sys

sys.path.insert(0, "/app/truth")

from fleet_registry import FleetRegistry, RegistryError, build  # noqa: E402

_MOUNT_DIR = "/app/truth"
_FILES = [
    f"{_MOUNT_DIR}/docker-compose.agents.yml",
    f"{_MOUNT_DIR}/docker-compose.agents-full.yml",
    f"{_MOUNT_DIR}/docker-compose.bropets.yml",
    f"{_MOUNT_DIR}/docker-compose.brain.yml",
]
_OVERLAY = f"{_MOUNT_DIR}/fleet_overlay.yml"


def _canonical_dict(registry: FleetRegistry) -> dict:
    return {
        "services": {
            name: {
                "host_port": svc.host_port,
                "container_port": svc.container_port,
                "source_file": svc.source_file,
                "profiles": sorted(svc.profiles),
            }
            for name, svc in sorted(registry.services.items())
        },
        "roster": sorted(registry.roster),
        "allowed_collisions": {
            port: sorted(names) for port, names in sorted(registry.allowed_collisions.items())
        },
    }


def get_snapshot_ref(files: list[str] | None = None, overlay_path: str | None = None) -> str:
    """Raises RegistryError / FileNotFoundError on any registry failure --
    never swallowed here. The caller (main.py) decides the terminal state
    (preview_unavailable) before ever calling the LLM or fleet-controller."""
    registry = build(files=files or _FILES, overlay_path=overlay_path or _OVERLAY)
    canonical = json.dumps(_canonical_dict(registry), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
