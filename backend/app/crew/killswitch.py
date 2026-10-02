"""Core's side of the fleet kill-switch: the off-box sentinel file, same semantics as the Governor's.

Opt-in: it does nothing unless ``CREW_KILL_FILE`` is set (the Governor's own default path is not assumed to be
mounted in core). When set, a run is stopped before its next step if the sentinel file exists, and, like the
Governor, an unknowable state is a killed state: if the sentinel's directory cannot be read the run stops.
Core does NOT read the Governor's Redis flag (that would be an unverified cross-service contract); the sentinel
file is the one that wins even if Redis is cleared.
"""

from __future__ import annotations

import os
from typing import Optional


def kill_reason() -> Optional[str]:
    """Why runs must stop right now, or None. Cheap (two stats): safe to call before every step."""
    path = os.getenv("CREW_KILL_FILE", "").strip()
    if not path:
        return None  # not configured: the check is off
    parent = os.path.dirname(path) or "."
    try:
        os.stat(parent)
    except OSError:
        return "kill sentinel directory is unreadable (an unknowable state counts as killed)"
    try:
        os.stat(path)
        return "kill switch engaged"
    except FileNotFoundError:
        return None  # directory is healthy and the file is genuinely absent
    except OSError:
        return "kill sentinel is unreadable (an unknowable state counts as killed)"
