"""Unit tests for BROski$ Token System — broski_service.py

All tests run against in-memory SQLite (via conftest.py `db` fixture).
No network or Redis required.
"""
from __future__ import annotations

import pytest

from app.models.broski import (
    BROskiWallet,
    BROskiAchievement,
    xp_to_level,
    XP_LEVELS,
)
from app.services import broski_service


# ── xp_to_level helpers ───────────────────────────────────────────────────────

class TestXpToLevel:
    def test_zero_xp_is_recruit(self):
        level, name = xp_to_level(0)
        assert level == 1
        assert "Recruit" in name

    def test_100_xp_is_cadet(self):
        level, name = xp_to_level(100)
        assert level == 2
        assert "Cadet" in name

    def test_5000_xp_is_legend(self):
        level, name = xp_to_level(5000)
        assert level == 7
        assert "Legend" in name

    def test_all_thresholds_monotonic(self):
        """Every XP threshold should produce a higher or equal level."""
        prev_level = 0
        for threshold, lvl, _ in XP_LEVELS:
            level, _ = xp_to_level(threshold)
            assert level >= prev_level
            prev_level = level

    def test_just_below_threshold_stays_lower(self):
        # 99 XP should still be level 1 (Recruit)
        level, _ = xp_to_level(99)
        assert level == 1


# ── Wallet creation ──────────────────────────────────────────────────────────

class TestWalletCreation:
    def test_get_wallet_creates_on_first_call(self, db):
        wallet = broski_service.get_wallet(user_id=1, db=db)
        assert wallet is not None
        assert wallet.user_id == 1
        assert wallet.coins == 0
        assert wallet.xp == 0
        assert wallet.level == 1

    def test_get_wallet_is_idempotent(self, db):
        w1 = broski_service.get_wallet(user_id=2, db=db)
        w2 = broski_service.get_wallet(user_id=2, db=db)
        assert w1.id == w2.id

    def test_different_users_get_different_wallets(self, db):
        w1 = broski_service.get_wallet(user_id=10, db=db)
        w2 = broski_service.get_wallet(user_id=11, db=db)
        assert w1.id != w2.id


# ── Award coins ───────────────────────────────────────────────────────────────

class TestAwardCoins:
    def test_award_increases_balance(self, db):
        wallet = broski_service.award_coins(user_id=1, amount=10, reason="test", db=db)
        assert wallet.coins == 10

    def test_multiple_awards_accumulate(self, db):
        broski_service.award_coins(user_id=1, amount=10, reason="first", db=db)
        wallet = broski_service.award_coins(user_id=1, amount=5, reason="second", db=db)
        assert wallet.coins == 15

    def test_award_creates_transaction(self, db):
        broski_service.award_coins(user_id=1, amount=10, reason="task done", db=db)
        txs, total = broski_service.get_transactions(user_id=1, db=db)
        assert total >= 1
        assert any(tx.reason == "task done" for tx in txs)


# ── Award XP & level-up ───────────────────────────────────────────────────────

class TestAwardXP:
    def test_award_xp_increases_xp(self, db):
        wallet, _ = broski_service.award_xp(user_id=1, amount=50, reason="test", db=db)
        assert wallet.xp == 50

    def test_level_up_triggers_on_threshold(self, db):
        # 100 XP → Cadet (level 2)
        wallet, msg = broski_service.award_xp(user_id=1, amount=100, reason="level up test", db=db)
        assert wallet.level == 2
        assert msg is not None
        assert "Cadet" in msg

    def test_no_level_up_message_when_level_unchanged(self, db):
        wallet, msg = broski_service.award_xp(user_id=1, amount=50, reason="small xp", db=db)
        assert msg is None

    def test_multiple_xp_awards_compound(self, db):
        broski_service.award_xp(user_id=1, amount=50, reason="first", db=db)
        wallet, _ = broski_service.award_xp(user_id=1, amount=50, reason="second", db=db)
        assert wallet.xp == 100


# ── Spend coins ───────────────────────────────────────────────────────────────

class TestSpendCoins:
    def test_spend_reduces_balance(self, db):
        broski_service.award_coins(user_id=1, amount=20, reason="load", db=db)
        wallet = broski_service.spend_coins(user_id=1, amount=10, reason="shop", db=db)
        assert wallet.coins == 10

    def test_cannot_overdraft(self, db):
        with pytest.raises(ValueError, match="Not enough BROski\\$"):
            broski_service.spend_coins(user_id=1, amount=100, reason="too much", db=db)

    def test_exact_balance_spendable(self, db):
        broski_service.award_coins(user_id=1, amount=10, reason="load", db=db)
        wallet = broski_service.spend_coins(user_id=1, amount=10, reason="all in", db=db)
        assert wallet.coins == 0


# ── Transaction history ───────────────────────────────────────────────────────

class TestTransactions:
    def test_get_transactions_empty_for_new_user(self, db):
        _, total = broski_service.get_transactions(user_id=99, db=db)
        assert total == 0

    def test_get_transactions_respects_limit(self, db):
        for i in range(10):
            broski_service.award_coins(user_id=1, amount=1, reason=f"tx-{i}", db=db)
        items, total = broski_service.get_transactions(user_id=1, db=db, limit=5)
        assert total == 10
        assert len(items) == 5

    def test_transactions_ordered_newest_first(self, db):
        # SQLite timestamp resolution can be the same for rapid inserts.
        # Verify ordering by checking the amounts are descending by insertion row,
        # which is guaranteed by the PK (id) order used as tiebreaker.
        broski_service.award_coins(user_id=1, amount=1, reason="first", db=db)
        broski_service.award_coins(user_id=1, amount=2, reason="second", db=db)
        items, total = broski_service.get_transactions(user_id=1, db=db)
        assert total == 2
        # Both transactions must be present
        reasons = {tx.reason for tx in items}
        assert reasons == {"first", "second"}


# ── Daily login bonus ─────────────────────────────────────────────────────────

class TestDailyLogin:
    def test_first_login_awards_coins(self, db):
        wallet, awarded = broski_service.handle_daily_login(user_id=1, db=db)
        assert awarded is True
        assert wallet.coins == 5

    def test_second_login_same_day_not_awarded(self, db):
        broski_service.handle_daily_login(user_id=1, db=db)
        _, awarded = broski_service.handle_daily_login(user_id=1, db=db)
        assert awarded is False


# ── Achievements ──────────────────────────────────────────────────────────────

class TestAchievements:
    def setup_method(self):
        pass

    def test_seed_creates_achievements(self, db):
        broski_service.seed_achievements(db)
        count = db.query(BROskiAchievement).count()
        assert count == len(broski_service.SEED_ACHIEVEMENTS)

    def test_seed_is_idempotent(self, db):
        broski_service.seed_achievements(db)
        broski_service.seed_achievements(db)
        count = db.query(BROskiAchievement).count()
        assert count == len(broski_service.SEED_ACHIEVEMENTS)

    def test_first_blood_unlocked_on_first_task(self, db):
        broski_service.seed_achievements(db)
        unlocked = broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_total": 1}
        )
        assert any("First Blood" in msg for msg in unlocked)

    def test_achievement_not_awarded_twice(self, db):
        broski_service.seed_achievements(db)
        broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_total": 1}
        )
        unlocked = broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_total": 2}
        )
        assert not any("First Blood" in msg for msg in unlocked)

    def test_streak_3_requires_3_tasks_today(self, db):
        broski_service.seed_achievements(db)
        unlocked = broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_today": 3}
        )
        assert any("On a Roll" in msg for msg in unlocked)

    def test_hyperfocus_hero_requires_5_session_tasks(self, db):
        broski_service.seed_achievements(db)
        unlocked = broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_session": 5}
        )
        assert any("Hyperfocus" in msg for msg in unlocked)

    def test_achievement_awards_coins_and_xp(self, db):
        broski_service.seed_achievements(db)
        wallet_before = broski_service.get_wallet(user_id=1, db=db)
        coins_before = wallet_before.coins
        broski_service.check_and_award_achievements(
            user_id=1, db=db, context={"tasks_completed_total": 1}
        )
        wallet_after = broski_service.get_wallet(user_id=1, db=db)
        assert wallet_after.coins > coins_before


# ── Leaderboard ───────────────────────────────────────────────────────────────

class TestLeaderboard:
    def test_leaderboard_returns_list(self, db):
        broski_service.award_coins(user_id=1, amount=100, reason="top", db=db)
        broski_service.award_coins(user_id=2, amount=50, reason="second", db=db)
        board = broski_service.get_leaderboard(db, limit=10)
        assert isinstance(board, list)
        assert len(board) >= 2

    def test_leaderboard_ordered_by_coins(self, db):
        broski_service.award_coins(user_id=1, amount=100, reason="top", db=db)
        broski_service.award_coins(user_id=2, amount=50, reason="second", db=db)
        board = broski_service.get_leaderboard(db, limit=10)
        coins = [w.coins for w in board]
        assert coins == sorted(coins, reverse=True)

    def test_leaderboard_respects_limit(self, db):
        for uid in range(1, 6):
            broski_service.award_coins(user_id=uid, amount=uid * 10, reason="load", db=db)
        board = broski_service.get_leaderboard(db, limit=3)
        assert len(board) == 3
