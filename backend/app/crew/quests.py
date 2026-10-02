"""Quest Settler: turns a finished, guard-ALLOWed crew run into a small, capped, idempotent reward.

Rules (design §7):
- Evidence or it didn't happen: pay only if the run's own history shows a sealed plan, a guard ALLOW
  and an evidence bundle whose hash still verifies against that run and plan.
- Only a human gets paid, and only the human who approved the plan. Agents and MCP clients have no
  path here: the settler runs as a flow node inside core, never as an endpoint.
- Un-farmable: ``source_id = run_id:quest_id`` is UNIQUE in the database, so a replay (restart,
  re-run, double call) settles at most once. A per-user daily XP ceiling bounds the rest.
- Never punitive: a retried run earns less but still earns; nothing here ever subtracts XP.
- Trust is not a reward: levels and achievements never touch safety review.

The numbers are small defaults for Lyndz to tune (open decision D1).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.broski_operator.recover_tools import _last_data
from app.crew.evidence import verify_bundle

logger = logging.getLogger(__name__)

QUEST_ID = "crew_run"
BASE_XP = 20
RETRIED_XP = 10  # a run where a step had to be re-run: still positive, no shaming
DAILY_XP_CAP = 100
COINS_PER_XP = 0.5

_SKIP_RETRY_NODES = ("approve",)  # a gate re-parked after a restart is not a retry

STATUS_AWARDED = "awarded"
STATUS_CAPPED = "capped"
STATUS_NO_AWARD = "no_award"


def source_id_for(run_id: str, quest_id: str = QUEST_ID) -> str:
    return f"{run_id}:{quest_id}"


@dataclass
class Evaluation:
    eligible: bool
    reason: str
    approver: str = ""
    bundle_hash: str = ""
    retried: bool = False
    signals: dict[str, bool] = field(default_factory=dict)


def _parse_ts(value: Any) -> Optional[datetime]:
    try:
        ts = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _panic_used_well(history: list[dict[str, Any]]) -> bool:
    """Paused and then resumed on the same (UTC) day, within this run."""
    paused_at: Optional[datetime] = None
    for e in history:
        if not isinstance(e, dict) or e.get("type") != "control":
            continue
        ts = _parse_ts(e.get("ts"))
        if ts is None:
            continue
        if e.get("status") == "paused":
            paused_at = ts
        elif e.get("status") == "resumed" and paused_at is not None and ts.date() == paused_at.date():
            return True
    return False


def _completed_counts(history: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in history:
        node = e.get("node") if isinstance(e, dict) else None
        if node and e.get("status") == "completed" and node not in _SKIP_RETRY_NODES:
            counts[node] = counts.get(node, 0) + 1
    return counts


def evaluate(run_id: str, history: list[dict[str, Any]]) -> Evaluation:
    """Decide from the run's own history. Deterministic; reads nothing else; fails closed."""
    sealed = _last_data(history, "seal") or {}
    guard = _last_data(history, "guard") or {}
    if sealed.get("sealed") is not True or not isinstance(sealed.get("plan_hash"), str):
        return Evaluation(False, "plan was never sealed")
    approver = sealed.get("approved_by")
    if not isinstance(approver, str) or not approver.strip():
        return Evaluation(False, "no recorded human approver")
    if guard.get("verdict") != "ALLOW" or guard.get("allowed") is not True or guard.get("failed_checks"):
        return Evaluation(False, "guard did not ALLOW this run")
    bundle = guard.get("evidence_bundle")
    if not isinstance(bundle, dict) or not verify_bundle(bundle):
        return Evaluation(False, "evidence bundle missing or does not verify")
    if bundle.get("run_id") != run_id or bundle.get("plan_hash") != sealed["plan_hash"]:
        return Evaluation(False, "evidence bundle is not for this run and plan")

    counts = _completed_counts(history)
    retried = any(n > 1 for n in counts.values())
    verify_once = counts.get("verify", 0) == 1
    return Evaluation(
        True,
        "guard ALLOW with a verified evidence bundle",
        approver=approver.strip(),
        bundle_hash=str(bundle["bundle_hash"]),
        retried=retried,
        signals={
            "zero_retry": not retried,
            "green_first_verify": verify_once,  # the guard already proved the verdict was PASS
            "panic_used_well": _panic_used_well(history),
        },
    )


def xp_for(ev: Evaluation) -> int:
    if not ev.eligible:
        return 0
    return RETRIED_XP if ev.retried else BASE_XP


@dataclass
class Settlement:
    status: str
    xp: int = 0
    coins: int = 0
    reason: str = ""
    already_settled: bool = False
    achievements: list[str] = field(default_factory=list)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def settle_run(
    db: Session,
    run_id: str,
    history: list[dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> Settlement:
    """Settle one run, at most once. Safe to call any number of times (restart, retry, replay)."""
    # Imported here: the economy service pulls in the wider app, and tests stub the DB per call.
    from app.models.broski import QuestSettlement
    from app.models.models import User
    from app.services import broski_service as eco

    now = now or datetime.now(timezone.utc)
    source_id = source_id_for(run_id)

    existing = db.query(QuestSettlement).filter_by(source_id=source_id).first()
    if existing is not None:
        return Settlement(existing.status, existing.xp, existing.coins, existing.reason, already_settled=True)

    ev = evaluate(run_id, history)
    user = None
    if ev.eligible:
        user = (
            db.query(User)
            .filter(User.email == ev.approver, User.is_active.is_(True), User.is_superuser.is_(True))
            .first()
        )
        if user is None:
            ev = Evaluation(False, "approver is not an active human account")

    wallet = eco.get_wallet(user.id, db) if user is not None else None  # may commit a new wallet; only a paid human gets one
    xp = coins = 0
    status = STATUS_NO_AWARD
    reason = ev.reason
    if ev.eligible and user is not None:
        used = (
            sum(
                r.xp
                for r in db.query(QuestSettlement)
                .filter(QuestSettlement.user_id == user.id, QuestSettlement.created_at >= _day_start(now))
                .all()
            )
        )
        room = max(0, DAILY_XP_CAP - used)
        want = xp_for(ev)
        xp = min(want, room)
        coins = int(xp * COINS_PER_XP)
        status = STATUS_AWARDED if xp > 0 else STATUS_CAPPED
        if xp < want:
            reason = "daily XP ceiling reached" if xp == 0 else "daily XP ceiling trimmed this award"

    row = QuestSettlement(
        source_id=source_id, run_id=run_id, quest_id=QUEST_ID, user_id=user.id if user else None,
        status=status, xp=xp, coins=coins, reason=reason[:255], bundle_hash=ev.bundle_hash or None,
        created_at=now,
    )
    db.add(row)
    try:
        db.flush()  # the UNIQUE(source_id) is the last line of defence against a concurrent settle
    except IntegrityError:
        db.rollback()
        again = db.query(QuestSettlement).filter_by(source_id=source_id).first()
        if again is None:
            raise
        return Settlement(again.status, again.xp, again.coins, again.reason, already_settled=True)

    achievements: list[str] = []
    if user is not None and wallet is not None and status != STATUS_NO_AWARD:
        if xp > 0:
            wallet.xp += xp
            wallet.coins += coins
            eco._log_transaction(
                wallet, xp, eco.TransactionType.earn, "Quest: crew run",
                db, {"source_id": source_id, "quest_id": QUEST_ID, "xp": xp, "coins": coins},
            )
            eco._check_level_up(wallet)
        db.commit()  # the settlement row and the award land together or not at all
        try:
            achievements = eco.check_and_award_achievements(
                user.id, db,
                {
                    "crew_runs_settled_total": 1,
                    "crew_zero_retry": ev.signals.get("zero_retry", False),
                    "crew_green_first_verify": ev.signals.get("green_first_verify", False),
                    "crew_panic_used_well": ev.signals.get("panic_used_well", False),
                },
            )
        except Exception:
            db.rollback()
            logger.warning("quest settler: achievement check failed for %s", source_id, exc_info=True)
    else:
        db.commit()
    return Settlement(status, xp, coins, reason, achievements=achievements)


HANDOVER_QUEST_ID = "handover_written"


def settle_handover(
    db: Session, run_id: str, history: list[dict[str, Any]], approver: str, *, now: Optional[datetime] = None
) -> Settlement:
    """Unlock "Handover Written" for the human who approved the Scribe's draft. Achievement only (0 XP here),
    at most once per run, and only for a run the Guardian allowed. The caller has already proved the approval
    was for exactly the drafted text."""
    from app.models.broski import QuestSettlement
    from app.models.models import User
    from app.services import broski_service as eco

    now = now or datetime.now(timezone.utc)
    source_id = source_id_for(run_id, HANDOVER_QUEST_ID)
    existing = db.query(QuestSettlement).filter_by(source_id=source_id).first()
    if existing is not None:
        return Settlement(existing.status, existing.xp, existing.coins, existing.reason, already_settled=True)

    ev = evaluate(run_id, history)
    user = (
        db.query(User)
        .filter(User.email == approver, User.is_active.is_(True), User.is_superuser.is_(True))
        .first()
        if ev.eligible else None
    )
    ok = user is not None
    reason = "handover drafted and approved" if ok else (ev.reason if not ev.eligible else "approver is not an active human account")
    db.add(QuestSettlement(
        source_id=source_id, run_id=run_id, quest_id=HANDOVER_QUEST_ID, user_id=user.id if user else None,
        status=STATUS_AWARDED if ok else STATUS_NO_AWARD, xp=0, coins=0, reason=reason, created_at=now,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        again = db.query(QuestSettlement).filter_by(source_id=source_id).first()
        if again is None:
            raise
        return Settlement(again.status, again.xp, again.coins, again.reason, already_settled=True)
    db.commit()
    achievements: list[str] = []
    if user is not None:
        try:
            achievements = eco.check_and_award_achievements(user.id, db, {"crew_handover_written": True})
        except Exception:
            db.rollback()
            logger.warning("quest settler: handover achievement failed for %s", source_id, exc_info=True)
    return Settlement(STATUS_AWARDED if ok else STATUS_NO_AWARD, 0, 0, reason, achievements=achievements)
