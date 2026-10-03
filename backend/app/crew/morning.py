"""The Morning Card ("Where was I?"): one Calm Card from what core already knows. Read-only.

Yesterday's wins, runs that are waiting on you or paused, and ONE traffic light for the machine. Exactly one
next action. No streaks, no "you missed a day", nothing to feel bad about: a quiet day reads as fine.
Deliberately uses only core's own data (settlements, run rows, free RAM). It does not call ``broski-coo``:
that adds a network hop with an unverified contract for a card that is useful without it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.broski_operator.catalog import TOOL_FLOWS
from app.broski_operator.runs import OPEN_STATUSES, pause_info
from app.crew.calm_card import CalmCard, CardStatus
from app.crew.quests import QUEST_ID
from app.models.broski import QuestSettlement
from app.models.hyperflow import HyperFlowRun

LIGHT_GREEN, LIGHT_AMBER, LIGHT_RED = "green", "amber", "red"
AMBER_HEADROOM = 1.5  # within 50% of the floor is "getting tight"


def traffic_light(available_mb: Optional[int], floor_mb: int) -> str:
    """Green / amber / red from free RAM. Unreadable is amber, never a confident green."""
    if available_mb is None:
        return LIGHT_AMBER
    if floor_mb > 0 and available_mb < floor_mb:
        return LIGHT_RED
    if floor_mb > 0 and available_mb < floor_mb * AMBER_HEADROOM:
        return LIGHT_AMBER
    return LIGHT_GREEN


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def build_morning_card(
    db: Session, *, now: Optional[datetime] = None, user_id: Optional[int],
    available_mb: Optional[int], floor_mb: int,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    light = traffic_light(available_mb, floor_mb)

    wins: list[QuestSettlement] = []
    if user_id is not None:  # an agent key has no wallet and sees no one's XP
        wins = (
            db.query(QuestSettlement)
            .filter(
                QuestSettlement.user_id == user_id, QuestSettlement.quest_id == QUEST_ID,
                QuestSettlement.status == "awarded", QuestSettlement.created_at >= now - timedelta(hours=24),
            )
            .order_by(QuestSettlement.created_at.desc())
            .all()
        )
    open_runs = (
        db.query(HyperFlowRun)
        .filter(HyperFlowRun.flow_name.in_(list(TOOL_FLOWS.values())), HyperFlowRun.status.in_(OPEN_STATUSES))
        .all()
    )
    held = [r for r in open_runs if pause_info(r) is not None]
    waiting = [r for r in open_runs if r.status == "awaiting_approval" and pause_info(r) is None]

    tldr: list[str] = []
    if wins:
        xp = sum(w.xp for w in wins)
        tldr.append(f"Last 24 hours: {_plural(len(wins), 'verified run', 'verified runs')}, +{xp} XP")
    else:
        tldr.append("Last 24 hours: a quiet one. That is fine.")
    if waiting:
        tldr.append(f"{_plural(len(waiting), 'run is', 'runs are')} waiting on you")
    if held:
        tldr.append(f"{_plural(len(held), 'run is', 'runs are')} paused and safe")
    free = "memory unreadable" if available_mb is None else f"{available_mb / 1024:.1f} GB free"
    tldr.append(f"Fleet: {light} ({free})")

    status: CardStatus
    if waiting:
        status, nxt = "waiting_on_you", "Open the run that is waiting on you"
    elif held:
        status, nxt = "paused", "Resume when you are ready"
    elif light == LIGHT_RED:
        status, nxt = "blocked", "Free some memory before starting anything"
    else:
        status, nxt = "done", "Start one small quest when you are ready"
    card = CalmCard(
        status=status, tldr=tldr, next_action=nxt,
        details=[f"Run {w.run_id[:8]}: +{w.xp} XP" for w in wins[:5]],
    )
    return {"calmCard": card.model_dump(), "light": light, "generatedAt": now.isoformat()}
