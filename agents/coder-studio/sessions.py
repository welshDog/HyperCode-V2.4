"""In-memory session store for coder-studio.

A session is one agent run against one throwaway worktree, plus the event log
and Shepherd decisions it produced. State lives only in the process — a restart
abandons in-flight worktrees, which ``prune_orphans`` sweeps on boot.

The store is deliberately tiny and synchronous; the FastAPI layer owns the async
work (running the agent, merging) and only mutates sessions through here.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from worktree import Worktree


class Status(str, Enum):
    PENDING = "pending"      # created, agent not started
    RUNNING = "running"      # agent working
    REVIEW = "review"        # agent done, diff awaiting human decision
    MERGED = "merged"        # landed on the base branch
    DISCARDED = "discarded"  # thrown away
    FAILED = "failed"        # agent errored


# The human may only act on a session that is sitting in REVIEW.
_MERGEABLE = {Status.REVIEW}


@dataclass
class Event:
    seq: int
    kind: str            # "message" | "decision" | "status" | "error"
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)


@dataclass
class Session:
    id: str
    prompt: str
    # Created lazily by the background run — a fresh worktree on a big
    # bind-mounted repo can take 10s+, far too long to block the POST that
    # starts the session. Until then the session is PENDING with no worktree.
    worktree: Optional[Worktree] = None
    status: Status = Status.PENDING
    events: list[Event] = field(default_factory=list)
    diff: Optional[str] = None
    merge_sha: Optional[str] = None
    # Stable per-session token so a replayed merge is a no-op, not a double-apply.
    idempotency_key: str = field(default_factory=lambda: secrets.token_hex(8))
    created_at: float = field(default_factory=time.time)
    _seq: int = 0

    def add_event(self, kind: str, data: dict[str, Any]) -> Event:
        self._seq += 1
        event = Event(seq=self._seq, kind=kind, data=data)
        self.events.append(event)
        return event

    def set_status(self, status: Status) -> None:
        self.status = status
        self.add_event("status", {"status": status.value})

    @property
    def is_mergeable(self) -> bool:
        return self.status in _MERGEABLE


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, prompt: str, worktree: Optional[Worktree] = None) -> Session:
        session = Session(id=f"cs_{secrets.token_hex(6)}", prompt=prompt, worktree=worktree)
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)

    def all(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())
