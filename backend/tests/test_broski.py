"""BROski$ Token System — Test Suite"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.models.broski import BROskiWallet, BROskiAchievement, xp_to_level, XP_LEVELS
from app.services import broski_service


# ── Fixtures ─────────────────────────────────────────────────────────────
def make_wallet(user_id: int = 1, coins: int = 0, xp: int = 0, level: int = 1) -> BROskiWallet:
    w = BROskiWallet()
    w.id = 1
    w.user_id = user_id
    w.coins = coins
    w.xp = xp
    w.level = level
    w.level_name = "BROski Recruit"
    w.transactions = []
    w.earned_achievements = []
    w.last_daily_login = None
    w.last_first_task_date = None
    return w


def make_db(wallet=None):
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = wallet
    db.query.return_value.filter_by.return_value.count.return_value = 0
    db.query.return_value.filter_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    return db


# ── Level system tests ─────────────────────────────────────────────────
class TestLevelSystem:
    def test_level_1_at_zero_xp(self):
        level, name = xp_to_level(0)
        assert level == 1
        assert name == "BROski Recruit"

    def test_level_2_at_100_xp(self):
        level, name = xp_to_level(100)
        assert level == 2
        assert name == "BROski Cadet"

    def test_level_7_at_5000_xp(self):
        level, name = xp_to_level(5000)
        assert level == 7
        assert "Legend" in name

    def test_level_stays_at_7_beyond_5000(self):
        level, _ = xp_to_level(99999)
        assert level == 7

    def test_level_4_at_499_xp(self):
        # Just below threshold for level 4 (500)
        level, _ = xp_to_level(499)
        assert level == 3

    def test_all_xp_thresholds_are_sorted(self):
        thresholds = [t for t, _, _ in XP_LEVELS]
        assert thresholds == sorted(thresholds)


# ── Wallet service tests ─────────────────────────────────────────────────
class TestWalletService:
    def test_get_wallet_creates_if_missing(self):
        db = make_db(wallet=None)
        wallet_obj = make_wallet()
        db.query.return_value.filter_by.return_value.first.return_value = None

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet_obj):
            result = broski_service.get_wallet(1, db)
        assert result.user_id == 1

    def test_award_coins_increases_balance(self):
        wallet = make_wallet(coins=10)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            result = broski_service.award_coins(1, 50, "test award", db)

        assert result.coins == 60

    def test_spend_coins_decreases_balance(self):
        wallet = make_wallet(coins=100)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            result = broski_service.spend_coins(1, 30, "test spend", db)

        assert result.coins == 70

    def test_spend_coins_raises_on_insufficient_balance(self):
        wallet = make_wallet(coins=5)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            with pytest.raises(ValueError, match="Not enough BROski"):
                broski_service.spend_coins(1, 100, "overspend", db)

    def test_award_xp_triggers_level_up(self):
        wallet = make_wallet(xp=90, level=1)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            result_wallet, level_msg = broski_service.award_xp(1, 20, "test xp", db)

        assert result_wallet.xp == 110
        assert result_wallet.level == 2
        assert level_msg is not None
        assert "LEVEL UP" in level_msg

    def test_award_xp_no_level_up(self):
        wallet = make_wallet(xp=10, level=1)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            _, level_msg = broski_service.award_xp(1, 5, "small xp", db)

        assert level_msg is None


# ── Achievement tests ─────────────────────────────────────────────────────
class TestAchievements:
    def _make_achievement(self, slug: str, xp: int = 50, coins: int = 20) -> BROskiAchievement:
        a = BROskiAchievement()
        a.slug = slug
        a.name = f"{slug} name"
        a.description = f"{slug} desc"
        a.xp_reward = xp
        a.coin_reward = coins
        return a

    def test_first_blood_awarded_after_first_task(self):
        wallet = make_wallet()
        db = make_db(wallet=wallet)
        achievement = self._make_achievement("first_blood")
        db.query.return_value.filter_by.return_value.first.side_effect = [
            wallet,  # _get_or_create_wallet
            achievement,  # fetch achievement definition
        ]

        with patch.object(broski_service, '_log_transaction'):
            unlocked = broski_service.check_and_award_achievements(
                1, db, context={"tasks_completed_total": 1}
            )
        assert any("first_blood" in m.lower() or "first" in m.lower() for m in unlocked)

    def test_no_duplicate_achievements(self):
        from app.models.broski import BROskiUserAchievement
        ua = BROskiUserAchievement()
        ua.achievement_slug = "first_blood"
        wallet = make_wallet()
        wallet.earned_achievements = [ua]
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet):
            unlocked = broski_service.check_and_award_achievements(
                1, db, context={"tasks_completed_total": 5}
            )
        # first_blood already earned, should NOT be in unlocked again
        assert not any("first_blood" in m.lower() for m in unlocked)

    def test_early_bird_context_flag(self):
        wallet = make_wallet()
        db = make_db(wallet=wallet)
        achievement = self._make_achievement("early_bird", xp=30, coins=10)
        db.query.return_value.filter_by.return_value.first.side_effect = [
            wallet, achievement
        ]

        with patch.object(broski_service, '_log_transaction'):
            unlocked = broski_service.check_and_award_achievements(
                1, db, context={"completed_before_9am": True}
            )
        assert any("early_bird" in m.lower() or "Early" in m for m in unlocked)

    def test_seed_achievements_idempotent(self):
        db = make_db()
        db.query.return_value.filter_by.return_value.first.return_value = MagicMock()  # already exists
        # Should not raise; should not add duplicates
        broski_service.seed_achievements(db)
        db.add.assert_not_called()


# ── Daily login tests ─────────────────────────────────────────────────────
class TestDailyLogin:
    def test_first_login_awards_coins(self):
        wallet = make_wallet(coins=0)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            result_wallet, awarded = broski_service.handle_daily_login(1, db)

        assert awarded is True
        assert result_wallet.coins == 5

    def test_second_login_within_24h_not_awarded(self):
        wallet = make_wallet(coins=5)
        wallet.last_daily_login = datetime.now(timezone.utc) - timedelta(hours=1)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet):
            result_wallet, awarded = broski_service.handle_daily_login(1, db)

        assert awarded is False
        assert result_wallet.coins == 5  # unchanged

    def test_login_after_24h_awards_again(self):
        wallet = make_wallet(coins=5)
        wallet.last_daily_login = datetime.now(timezone.utc) - timedelta(hours=25)
        db = make_db(wallet=wallet)

        with patch.object(broski_service, '_get_or_create_wallet', return_value=wallet), \
             patch.object(broski_service, '_log_transaction'):
            result_wallet, awarded = broski_service.handle_daily_login(1, db)

        assert awarded is True
        assert result_wallet.coins == 10
