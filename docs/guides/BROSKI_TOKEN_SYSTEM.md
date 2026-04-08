# 🔥 BROski$ Token System — User Guide

> **TL;DR:** Do stuff. Earn coins. Level up. Unlock achievements. Be legendary.

---

## 🤔 What is BROski$?

BROski$ is the **gamification engine** inside HyperCode.

- Complete tasks → earn **coins** + **XP**
- Earn enough XP → **level up**
- Hit milestones → **unlock achievements**
- Top the **leaderboard** 🏅

Built for ADHD + neurodivergent minds — every small win matters!

---

## 💰 How to Earn Coins + XP

| Action | Coins | XP |
|---|---|---|
| Complete a task | +10 | +25 |
| Create a task | +2 | — |
| Start a mission | +5 | — |
| Daily login | +5 | — |
| First task of the day | — | +15 bonus |
| Unlock achievement | varies | varies |

---

## ⬆️ Level System

| XP | Level | Title |
|---|---|---|
| 0 | 1 | BROski Recruit |
| 100 | 2 | BROski Cadet |
| 250 | 3 | BROski Agent |
| 500 | 4 | BROski Operator |
| 1000 | 5 | BROski Commander |
| 2000 | 6 | BROski Architect |
| 5000 | 7 | BROski Legend ♾️ |

When you level up, you'll see:
> **"LEVEL UP BROski! You're now a BROski Operator! 🔥"**

---

## 🏆 Achievements (v1 Starter Set)

| Achievement | How to unlock | XP | Coins |
|---|---|---|---|
| 🩸 First Blood | Complete your first task | +50 | +20 |
| 🔥 On a Roll | 3 tasks in one day | +100 | +30 |
| 🚀 Mission Launched | Start your first mission | +75 | +25 |
| 🦅 Hyperfocus Hero | 5 tasks in one session | +150 | +50 |
| ☀️ Early Bird | Complete a task before 9 AM | +30 | +10 |

When you unlock one, you'll see:
> **"Achievement unlocked: Hyperfocus Hero! Complete 5 tasks in one session — absolute beast mode! 🏆"**

---

## 🔧 API Endpoints

All endpoints are at `/api/v1/broski/` and require a **JWT token** in the header:
```
Authorization: Bearer <your_token>
```

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/broski/wallet` | Your coins, XP, level |
| GET | `/broski/transactions` | Your full coin history |
| GET | `/broski/achievements` | All available achievements |
| GET | `/broski/achievements/me` | Achievements you've earned |
| GET | `/broski/leaderboard` | Top 10 players |
| POST | `/broski/award` | (Admin only) Award coins/XP |
| POST | `/broski/daily-login` | Claim your daily +5 coins |

---

## ⚠️ Error Messages (friendly ones!)

- **Not enough coins:** `"Not enough BROski$ coins — you need X more! 💸"`
- **Already claimed daily:** `"Already claimed today — come back tomorrow for more coins! ⏰"`
- **Unauthorized award:** `"Only admins and agents can award BROski$ coins directly."`

---

## 🚀 For Developers — Wiring Event Hooks

When a task is completed in `tasks.py`, fire these:

```python
from app.services import broski_service

# On task complete:
broski_service.award_coins(user_id, 10, "Task completed", db)
broski_service.award_xp(user_id, 25, "Task completed", db)

# On task create:
broski_service.award_coins(user_id, 2, "Task created", db)

# On mission start:
broski_service.award_coins(user_id, 5, "Mission started", db)
```

Pass context to `check_and_award_achievements()` to evaluate badges:

```python
broski_service.check_and_award_achievements(
    user_id=user.id,
    db=db,
    context={
        "tasks_completed_total": user_task_count,
        "tasks_completed_today": today_count,
        "missions_started_total": missions_count,
        "tasks_completed_session": session_count,
        "completed_before_9am": hour < 9,
    }
)
```

---

## 🧪 Running Tests

```bash
pytest backend/tests/test_broski.py -v
```

Expect **15+ passing tests** covering: wallet, XP/levels, coin awarding/spending, achievements, daily login.

---

## 📅 Running the Migration

```bash
cd backend
alembic upgrade head
```

This creates 4 tables: `broski_wallets`, `broski_transactions`, `broski_achievements`, `broski_user_achievements`.

---

*BROski Power Level: LEGENDARY ♾️🔥*
