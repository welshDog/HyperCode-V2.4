"""Which containers `hypercode.recover` may propose restarting (default-deny).

Pure policy — no Docker, no IO. The never-list always wins over the allow-list and the
opt-in label. Undecided containers (e.g. celery-worker, hypercode-dashboard) are NOT eligible
until Bro decides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

RESTARTABLE_LABEL = "hypercode.recover"
RESTARTABLE_LABEL_VALUE = "restartable"

# Recovery infrastructure, data stores, safety/governance and the operator's own entry points.
NEVER_LIST = frozenset(
    {
        "hypercode-core",
        "postgres",
        "redis",
        "docker-socket-proxy",
        "docker-socket-proxy-build",
        "docker-socket-proxy-healer",
        "safety-shepherd",
        "governor",
        "fleet-controller",
        "crew-orchestrator",
        "hypercode-mcp-server",
        "hypercode-ollama",
        "agent-registry",
        "healer-agent",
    }
)

ALLOW_LIST = frozenset(
    {
        "agent-focus-tracker",
        "agent-hyper-brain-core",
        "agent-mcp-bridge",
        "agent-morning-briefing",
        "broski-bot",
        "chroma",
        "coder-studio",
        "evolve-relay",
        "github-sync",
        "github-sync-brain",
        "hyper-brain",
        "hyperhealth-worker",
        "memstream",
        "obsidian-watcher",
        "skillweaver",
    }
)


@dataclass(frozen=True)
class Eligibility:
    allowed: bool
    basis: Optional[str] = None       # "allow_list" | "label"
    blocked_by: Optional[str] = None  # "never_list" | "not_allowlisted"

    def as_dict(self) -> dict:
        return {"allowed": self.allowed, "basis": self.basis, "blocked_by": self.blocked_by}


def classify(name: str, labels: Optional[Mapping[str, str]] = None) -> Eligibility:
    if name in NEVER_LIST:
        return Eligibility(False, None, "never_list")
    if name in ALLOW_LIST:
        return Eligibility(True, "allow_list", None)
    if (labels or {}).get(RESTARTABLE_LABEL) == RESTARTABLE_LABEL_VALUE:
        return Eligibility(True, "label", None)
    return Eligibility(False, None, "not_allowlisted")
