"""IdentityAgent — a resident agent object per user (P1-1).

Every Discord/course user has a `broski_identity_agents` row. The IdentityAgent
wraps it with behaviour:

  * award_tokens(amount, reason, source_id) — logs then wraps the durable
    broski_service.award_xp (postgres-backed wallet/transactions).
  * check_permission(action) -> bool — consults the user's granted permissions.
  * log_action(tool, payload, decision) — records a high-impact action.

High-impact actions (token award, shop purchase, agent task dispatch) should
call log_action() before executing. Full audit persistence (governance_ledger)
is P1-2; for now actions are logged structured + kept in a capped in-state ring.

Usage::

    agent = IdentityAgent.get_or_create(user_id, db)
    if agent.check_permission("shop.purchase"):
        agent.award_tokens(50, "quest complete", source_id="quest:42", db=db)

Import path::  from app.agents.identity_agent import IdentityAgent
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.identity import BROskiIdentityAgent
from app.models.models import User
from app.services import broski_service

logger = logging.getLogger(__name__)

MAX_RECENT_ACTIONS = 50

# Header carried on internal API calls that touch user state.
IDENTITY_HEADER = "X-BROSKI-IDENTITY"


class IdentityAgent:
    def __init__(self, record: BROskiIdentityAgent, db: Session) -> None:
        self._record = record
        self._db = db

    # ── provisioning ─────────────────────────────────────────────────────────

    @classmethod
    def get_or_create(cls, user_id: int, db: Session) -> "IdentityAgent":
        record = (
            db.query(BROskiIdentityAgent)
            .filter(BROskiIdentityAgent.user_id == user_id)
            .one_or_none()
        )
        if record is None:
            user = db.get(User, user_id)
            record = BROskiIdentityAgent(
                user_id=user_id,
                discord_id=getattr(user, "discord_id", None) if user else None,
                state={"tier": "free", "permissions": {}, "recent_actions": []},
                last_active=datetime.now(timezone.utc),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            logger.info("🪪 Provisioned IdentityAgent for user %s", user_id)
        return cls(record, db)

    # ── accessors ────────────────────────────────────────────────────────────

    @property
    def user_id(self) -> int:
        return self._record.user_id

    @property
    def discord_id(self) -> Optional[str]:
        return self._record.discord_id

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._record.state or {})

    def identity_header(self) -> dict[str, str]:
        """Header to attach to internal API calls that touch this user's state."""
        return {IDENTITY_HEADER: self.discord_id or str(self.user_id)}

    # ── behaviour ────────────────────────────────────────────────────────────

    def check_permission(self, action: str) -> bool:
        """Allow by default; deny only if explicitly listed under permissions.deny.

        permissions = { "deny": ["shop.refund", ...], "allow": [...] }
        An explicit allow-list (when present) restricts to listed actions.
        """
        perms = (self._record.state or {}).get("permissions", {}) or {}
        deny = set(perms.get("deny", []) or [])
        allow = perms.get("allow")
        if action in deny:
            return False
        if isinstance(allow, list) and allow:
            return action in allow
        return True

    def log_action(self, tool: str, payload: dict[str, Any], decision: str) -> dict[str, Any]:
        """Record a high-impact action against this identity (call BEFORE executing)."""
        entry = {
            "tool": tool,
            "payload": payload,
            "decision": decision,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        state = dict(self._record.state or {})
        ring = list(state.get("recent_actions", []))
        ring.append(entry)
        state["recent_actions"] = ring[-MAX_RECENT_ACTIONS:]
        self._record.state = state
        self._record.last_active = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(self._record)
        logger.info(
            "🪪 identity %s action=%s decision=%s", self.user_id, tool, decision
        )
        return entry

    def touch(self) -> None:
        self._record.last_active = datetime.now(timezone.utc)
        self._db.commit()

    def award_tokens(
        self,
        amount: int,
        reason: str,
        source_id: str,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """Log + award durable BROski$ XP (wraps broski_service.award_xp)."""
        sess = db or self._db
        if not self.check_permission("tokens.award"):
            self.log_action("award_tokens", {"amount": amount, "reason": reason}, "BLOCK")
            raise PermissionError("award_tokens denied for this identity")
        self.log_action(
            "award_tokens",
            {"amount": amount, "reason": reason, "source_id": source_id},
            "ALLOW",
        )
        wallet, level_up = broski_service.award_xp(
            user_id=self.user_id,
            amount=amount,
            reason=reason,
            db=sess,
            meta={"source_id": source_id, "via": "identity_agent"},
        )
        return {
            "user_id": self.user_id,
            "xp": wallet.xp,
            "level": wallet.level,
            "level_name": wallet.level_name,
            "level_up": level_up,
        }
