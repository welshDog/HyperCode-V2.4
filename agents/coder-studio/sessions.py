"""In-memory session store for coder-studio.

A session is one agent run against one throwaway worktree, plus the event log
and Shepherd decisions it produced. State lives only in the process — a restart
abandons in-flight worktrees, which ``prune_orphans`` sweeps on boot.

The store is deliberately tiny and synchronous; the FastAPI layer owns the async
work (running the agent, merging) and only mutates sessions through here.

Memory ceiling:
  ``SessionStore(max_sessions=N, ttl=T)`` enforces a hard cap. When the store
  reaches capacity, _evict() removes expired terminal sessions first, then prunes
  by status priority (safest first) to make room for the next create(). RUNNING
  sessions are only evicted as a last resort — they have live worktrees.
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

# Eviction priority: safest (no live worktree, terminal) to riskiest (live).
_EVICTION_ORDER = [
    Status.DISCARDED,
    Status.MERGED,
    Status.FAILED,
    Status.REVIEW,
    Status.PENDING,
    Status.RUNNING,  # last resort — has a live worktree
]


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
        event = Event(seq=self._seq, kind=kind, data=data.copy())
        self.events.append(event)
        return event

    def set_status(self, status: Status) -> None:
        self.status = status
        self.add_event("status", {"status": status.value})

    @property
    def is_mergeable(self) -> bool:
        return self.status in _MERGEABLE


class SessionStore:
    def __init__(
        self,
        max_sessions: int = 200,
        ttl: int = 24 * 3600,
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._max = max_sessions
        self._ttl = ttl

    def _evict(self) -> None:
        """Remove old/terminal sessions when the store is at or above capacity.

        Must be called with self._lock held.
        """
        now = time.time()
        cutoff = now - self._ttl

        # 1. Always sweep TTL-expired terminal sessions — they cost memory but
        #    can never be acted on by the user.
        expired = [
            sid for sid, s in self._sessions.items()
            if s.created_at < cutoff
            and s.status in (Status.MERGED, Status.DISCARDED, Status.FAILED)
        ]
        for sid in expired:
            del self._sessions[sid]

        # 2. If still at the hard cap, evict by status priority oldest-first.
        if len(self._sessions) >= self._max:
            by_status: dict[Status, list[tuple[str, Session]]] = {s: [] for s in Status}
            for sid, s in self._sessions.items():
                by_status[s.status].append((sid, s))

            for status in _EVICTION_ORDER:
                if len(self._sessions) < self._max:
                    break
                candidates = sorted(by_status[status], key=lambda x: x[1].created_at)
                for sid, _ in candidates:
                    if len(self._sessions) < self._max:
                        break
                    del self._sessions[sid]

    def create(self, prompt: str, worktree: Optional[Worktree] = None) -> Session:
        session = Session(id=f"cs_{secrets.token_hex(6)}", prompt=prompt, worktree=worktree)
        with self._lock:
            self._evict()
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)

    def all(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())
