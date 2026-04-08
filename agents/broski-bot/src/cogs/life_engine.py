"""
Life Engine Cog — Hyper-life simulation for BROski World.

Features:
  - Brain modes (ADHD productivity modes)
  - Vibe tracking (energy/mood system)
  - Hyperdash (personal command centre)
  - Life stats (full simulation dashboard)
  - Mission spawner (dynamic quest generation)
  - Auto-XP rewards for server activity
  - Real-time leaderboard
  - Streak tracking
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy import select, func as sqlfunc

from src.config.logging import get_logger
from src.config.settings import settings
from src.core.database import get_db_session
from src.models import User, Economy, Transaction, FocusSession

logger = get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

BRAIN_MODES = {
    "hyperfocus": {
        "emoji": "⚡",
        "label": "HYPERFOCUS",
        "desc": "Maximum output mode. Zero distractions. Beast mode ON.",
        "colour": 0x9b59b6,
        "xp_multiplier": 2.0,
        "tips": [
            "Close all social apps except this one",
            "Set a 25-min timer — GO",
            "Keep water nearby, skip snacks for now",
        ],
    },
    "chill": {
        "emoji": "🌊",
        "label": "CHILL MODE",
        "desc": "Low-pressure flow. Light tasks, creative drift, recharge.",
        "colour": 0x3498db,
        "xp_multiplier": 1.0,
        "tips": [
            "Pick one easy task to chip away at",
            "Lo-fi music helps — try it",
            "No pressure, just vibe",
        ],
    },
    "creative": {
        "emoji": "🎨",
        "label": "CREATIVE STORM",
        "desc": "Ideas-first mode. Capture everything, judge nothing.",
        "colour": 0xe67e22,
        "xp_multiplier": 1.5,
        "tips": [
            "Brain dump into a notes doc first",
            "Switch between tasks freely — that's valid",
            "Colour-code or sketch if typing feels slow",
        ],
    },
    "grind": {
        "emoji": "🔥",
        "label": "GRIND MODE",
        "desc": "Structured hustle. Hit targets, log progress, stack wins.",
        "colour": 0xe74c3c,
        "xp_multiplier": 1.75,
        "tips": [
            "Write your 3 must-do tasks RIGHT NOW",
            "Block your calendar for 90 min",
            "Every completed task = quick reward (coffee, stretch, message a friend)",
        ],
    },
    "rest": {
        "emoji": "💤",
        "label": "REST MODE",
        "desc": "Recovery is productive. Recharge so tomorrow slaps.",
        "colour": 0x2ecc71,
        "xp_multiplier": 0.5,
        "tips": [
            "Screen-free 10 min after this",
            "Drink water, seriously",
            "You've earned this — no guilt",
        ],
    },
}

VIBES = ["🔥 On Fire", "⚡ Charged Up", "😎 Smooth", "🌊 Flowing", "😴 Tired", "🤯 Overwhelmed", "🧘 Zen", "🎯 Locked In", "😤 Frustrated", "🚀 Launching"]

MISSION_POOL = [
    {"title": "First Blood", "desc": "Send 5 messages in the server today.", "reward": 75, "req": "messages", "count": 5},
    {"title": "Social Butterfly", "desc": "React to 3 different messages.", "reward": 50, "req": "reactions", "count": 3},
    {"title": "Focus Warrior", "desc": "Complete a focus session of any length.", "reward": 150, "req": "focus_session", "count": 1},
    {"title": "Daily Grind", "desc": "Claim your daily BROski$ reward.", "reward": 25, "req": "daily_claim", "count": 1},
    {"title": "Hyperfocus Legend", "desc": "Complete a 45+ min focus session.", "reward": 400, "req": "focus_45min", "count": 1},
    {"title": "Economy Player", "desc": "Give BROski$ to another member.", "reward": 100, "req": "transfer", "count": 1},
    {"title": "Streak Keeper", "desc": "Maintain a 3-day daily login streak.", "reward": 200, "req": "streak", "count": 3},
    {"title": "Night Owl", "desc": "Send a message after 10pm UTC.", "reward": 60, "req": "night_message", "count": 1},
    {"title": "Speed Runner", "desc": "Use 3 slash commands in under 5 minutes.", "reward": 80, "req": "fast_commands", "count": 3},
    {"title": "BROski Champion", "desc": "Reach the top 3 on the XP leaderboard.", "reward": 500, "req": "leaderboard_top3", "count": 1},
]

XP_PER_MESSAGE = 3
XP_LEVEL_BASE = 100  # XP needed for level 2; each level = level * XP_LEVEL_BASE


def xp_for_level(level: int) -> int:
    return level * XP_LEVEL_BASE


def level_from_xp(xp: int) -> int:
    level = 1
    total = 0
    while True:
        needed = xp_for_level(level)
        if total + needed > xp:
            break
        total += needed
        level += 1
    return level


# ─── Cog ──────────────────────────────────────────────────────────────────────

class LifeEngine(commands.Cog, name="LifeEngine"):
    """Hyper-life simulation engine for BROski World."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory brain modes & vibes per user (resets on restart — that's fine)
        self._brain_modes: dict[int, str] = {}  # user_id → mode key
        self._vibes: dict[int, str] = {}         # user_id → vibe string
        self._message_counts: dict[int, int] = {}  # user_id → message count today
        self._command_times: dict[int, list] = {}   # user_id → list of recent command timestamps
        self.leaderboard_refresh.start()

    def cog_unload(self):
        self.leaderboard_refresh.cancel()

    # ─── Brain Modes ──────────────────────────────────────────────

    @app_commands.command(name="brain_mode", description="Set your ADHD brain mode for the session")
    @app_commands.describe(mode="Choose your mode: hyperfocus, chill, creative, grind, rest")
    @app_commands.choices(mode=[
        app_commands.Choice(name="⚡ Hyperfocus — beast mode", value="hyperfocus"),
        app_commands.Choice(name="🌊 Chill — low pressure flow", value="chill"),
        app_commands.Choice(name="🎨 Creative — ideas storm", value="creative"),
        app_commands.Choice(name="🔥 Grind — structured hustle", value="grind"),
        app_commands.Choice(name="💤 Rest — recovery mode", value="rest"),
    ])
    async def brain_mode(self, interaction: discord.Interaction, mode: str):
        m = BRAIN_MODES[mode]
        self._brain_modes[interaction.user.id] = mode

        embed = discord.Embed(
            title=f"{m['emoji']} {m['label']} ACTIVATED",
            description=m["desc"],
            color=m["colour"],
        )
        embed.add_field(
            name="💡 Tips for this mode",
            value="\n".join(f"• {t}" for t in m["tips"]),
            inline=False,
        )
        embed.add_field(
            name="⚡ XP Multiplier",
            value=f"**{m['xp_multiplier']}x** while in this mode",
            inline=True,
        )
        embed.set_footer(text=f"Mode set for {interaction.user.display_name} | BROski Life Engine")
        await interaction.response.send_message(embed=embed)
        logger.info("Brain mode set", user=str(interaction.user), mode=mode)

    @app_commands.command(name="vibe", description="Check in with your current vibe/energy level")
    @app_commands.describe(mood="Pick the vibe that matches your energy right now")
    @app_commands.choices(mood=[
        app_commands.Choice(name=v, value=v) for v in VIBES
    ])
    async def vibe(self, interaction: discord.Interaction, mood: str):
        self._vibes[interaction.user.id] = mood
        brain = self._brain_modes.get(interaction.user.id)
        brain_info = f"\n**Brain Mode:** {BRAIN_MODES[brain]['emoji']} {BRAIN_MODES[brain]['label']}" if brain else ""

        embed = discord.Embed(
            title=f"Vibe Check: {mood}",
            description=f"**{interaction.user.display_name}** is feeling **{mood}**{brain_info}",
            color=0x1abc9c,
        )

        # Contextual suggestion
        if "overwhelmed" in mood.lower() or "frustrated" in mood.lower():
            embed.add_field(name="💙 Suggested", value="Try `/anxietycheck` or switch to 💤 Rest mode with `/brain_mode rest`", inline=False)
        elif "tired" in mood.lower():
            embed.add_field(name="💤 Suggested", value="Rest mode activated? Use `/brain_mode rest` — recovery IS productive", inline=False)
        elif "fire" in mood.lower() or "charged" in mood.lower() or "launching" in mood.lower():
            embed.add_field(name="⚡ Suggested", value="You're on fire! Activate `/brain_mode hyperfocus` and `/focus` now!", inline=False)

        embed.set_footer(text="BROski Life Engine • vibe tracking 🐶♾️")
        await interaction.response.send_message(embed=embed)

    # ─── Life Stats ───────────────────────────────────────────────

    @app_commands.command(name="life_stats", description="Full life simulation stats — your complete BROski dashboard")
    @app_commands.describe(member="Member to view (default: yourself)")
    async def life_stats(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()
        target = member or interaction.user
        user_id = target.id

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                await interaction.followup.send(f"❌ No data for **{target.display_name}** yet — they need to use a command first!")
                return

            # Focus stats
            focus_result = await session.execute(
                select(
                    sqlfunc.count(FocusSession.id),
                    sqlfunc.sum(FocusSession.duration_minutes),
                    sqlfunc.sum(FocusSession.tokens_earned),
                ).where(FocusSession.user_id == user_id, FocusSession.is_active == False)
            )
            focus_count, focus_mins, focus_coins = focus_result.one()
            focus_count = focus_count or 0
            focus_mins = focus_mins or 0
            focus_coins = focus_coins or 0

        level = level_from_xp(user.xp)
        xp_in_level = user.xp - sum(xp_for_level(l) for l in range(1, level))
        xp_needed = xp_for_level(level)
        bar_fill = int((xp_in_level / xp_needed) * 20) if xp_needed else 0
        xp_bar = "█" * bar_fill + "░" * (20 - bar_fill)

        brain = self._brain_modes.get(user_id)
        vibe = self._vibes.get(user_id, "Unknown")
        brain_label = f"{BRAIN_MODES[brain]['emoji']} {BRAIN_MODES[brain]['label']}" if brain else "Not set"

        embed = discord.Embed(
            title=f"🌐 {target.display_name}'s Life Stats",
            color=0x9b59b6,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="⚡ Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ XP", value=f"**{user.xp:,}** total", inline=True)
        embed.add_field(name="💬 Messages", value=f"**{user.total_messages:,}**", inline=True)

        balance = user.economy.balance if user.economy else 0
        lifetime = user.economy.lifetime_earned if user.economy else 0
        streak = user.economy.daily_streak if user.economy else 0
        max_streak = user.economy.max_daily_streak if user.economy else 0
        crystals = user.economy.memory_crystals if user.economy else 0

        embed.add_field(name="💰 BROski$", value=f"**{balance:,}**", inline=True)
        embed.add_field(name="🏦 Lifetime Earned", value=f"**{lifetime:,}**", inline=True)
        embed.add_field(name="💎 Memory Crystals", value=f"**{crystals}**", inline=True)

        embed.add_field(name="🔥 Daily Streak", value=f"**{streak}** days (best: **{max_streak}**)", inline=True)
        embed.add_field(name="🧠 Brain Mode", value=brain_label, inline=True)
        embed.add_field(name="🌊 Vibe", value=vibe, inline=True)

        embed.add_field(
            name="⏱️ Focus Sessions",
            value=f"**{focus_count}** sessions | **{focus_mins}** min total | **{focus_coins:,} BROski$** earned",
            inline=False,
        )
        embed.add_field(
            name=f"📊 Level Progress — {level} → {level+1}",
            value=f"`{xp_bar}` {xp_in_level}/{xp_needed} XP",
            inline=False,
        )

        embed.set_footer(text=f"BROski Life Engine v4.0 • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)

    # ─── Hyperdash ────────────────────────────────────────────────

    @app_commands.command(name="hyperdash", description="Your personal BROski command centre — all quick actions in one place")
    async def hyperdash(self, interaction: discord.Interaction):
        brain = self._brain_modes.get(interaction.user.id)
        vibe = self._vibes.get(interaction.user.id, "Not set")
        brain_label = f"{BRAIN_MODES[brain]['emoji']} {BRAIN_MODES[brain]['label']}" if brain else "Not set — try `/brain_mode`"

        embed = discord.Embed(
            title=f"🚀 {interaction.user.display_name}'s HyperDash",
            description="Your personal control centre. Everything in one place.",
            color=0x2c3e50,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.add_field(name="🧠 Brain Mode", value=brain_label, inline=True)
        embed.add_field(name="🌊 Vibe", value=vibe, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(
            name="💰 Economy",
            value="`/balance` • `/daily` • `/give` • `/leaderboard`",
            inline=False,
        )
        embed.add_field(
            name="⏱️ Focus",
            value="`/focus <project>` • `/focusend` • `/hyperfocus <task>`",
            inline=False,
        )
        embed.add_field(
            name="🌐 Life Engine",
            value="`/brain_mode` • `/vibe` • `/life_stats` • `/spawn_mission` • `/streak`",
            inline=False,
        )
        embed.add_field(
            name="🤖 AI Coach",
            value="`/coach <topic>` • `/motivate` • `/anxietycheck`",
            inline=False,
        )
        embed.add_field(
            name="🏆 Progression",
            value="`/quests` • `/achievements` • `/rank`",
            inline=False,
        )

        embed.set_footer(text="BROski Life Engine • HyperDash v4.0 🐶♾️")
        await interaction.response.send_message(embed=embed)

    # ─── Mission Spawner ──────────────────────────────────────────

    @app_commands.command(name="spawn_mission", description="Spawn a random hyper-mission — complete it for BROski$ rewards")
    async def spawn_mission(self, interaction: discord.Interaction):
        mission = random.choice(MISSION_POOL)
        brain = self._brain_modes.get(interaction.user.id)
        multiplier = BRAIN_MODES[brain]["xp_multiplier"] if brain else 1.0
        bonus_reward = int(mission["reward"] * multiplier)

        embed = discord.Embed(
            title=f"🎯 MISSION SPAWNED: {mission['title']}",
            description=mission["desc"],
            color=0xe67e22,
        )
        embed.add_field(name="💰 Base Reward", value=f"**{mission['reward']} BROski$**", inline=True)
        if multiplier > 1.0:
            embed.add_field(name=f"⚡ Mode Bonus ({multiplier}x)", value=f"**+{bonus_reward - mission['reward']} BROski$**", inline=True)
        embed.add_field(name="🏆 Total Reward", value=f"**{bonus_reward} BROski$**", inline=True)
        embed.add_field(name="📋 Requirement", value=f"`{mission['req']}` × {mission['count']}", inline=False)
        embed.set_footer(text="Missions tracked by BROski | Use /quests for persistent quests")
        await interaction.response.send_message(embed=embed)

    # ─── Streak Viewer ────────────────────────────────────────────

    @app_commands.command(name="streak", description="View your current streaks and bonus projections")
    async def streak(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

        if not user or not user.economy:
            await interaction.followup.send("❌ No streak data yet — use `/daily` to start your streak!")
            return

        eco = user.economy
        streak = eco.daily_streak
        max_streak = eco.max_daily_streak
        next_bonus = 50 * (streak + 1)
        milestone_next = next(
            (s for s in [7, 14, 30, 60, 100] if s > streak), None
        )

        embed = discord.Embed(
            title=f"🔥 {interaction.user.display_name}'s Streaks",
            color=0xe74c3c,
        )
        embed.add_field(name="🔥 Daily Streak", value=f"**{streak}** days", inline=True)
        embed.add_field(name="🏆 Best Streak", value=f"**{max_streak}** days", inline=True)
        embed.add_field(name="💰 Tomorrow's Bonus", value=f"**+{next_bonus} BROski$**", inline=True)

        if milestone_next:
            days_to_milestone = milestone_next - streak
            embed.add_field(
                name=f"🎯 Next Milestone: {milestone_next} days",
                value=f"**{days_to_milestone}** more day(s) to go!",
                inline=False,
            )

        # Streak fire bar
        fire_bar = "🔥" * min(streak, 10) + "⬜" * max(0, 10 - streak)
        embed.add_field(name="Progress (10-day bar)", value=fire_bar, inline=False)
        embed.set_footer(text="Use /daily every day to keep your streak alive!")
        await interaction.followup.send(embed=embed)

    # ─── Rank Command ─────────────────────────────────────────────

    @app_commands.command(name="rank", description="View your rank and level card")
    @app_commands.describe(member="Member to check (default: yourself)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()
        target = member or interaction.user
        user_id = target.id

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            # Get user rank by XP
            rank_result = await session.execute(
                select(sqlfunc.count(User.id)).where(User.xp > (user.xp if user else 0))
            )
            rank_num = (rank_result.scalar() or 0) + 1

        if not user:
            await interaction.followup.send(f"❌ **{target.display_name}** has no data yet.")
            return

        level = level_from_xp(user.xp)
        xp_in_level = user.xp - sum(xp_for_level(l) for l in range(1, level))
        xp_needed = xp_for_level(level)
        bar_fill = int((xp_in_level / xp_needed) * 15) if xp_needed else 0
        xp_bar = "█" * bar_fill + "░" * (15 - bar_fill)

        rank_badge = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank_num, f"#{rank_num}")

        embed = discord.Embed(
            title=f"🏆 Rank Card — {target.display_name}",
            color=0xf1c40f,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏅 Server Rank", value=f"**{rank_badge}**", inline=True)
        embed.add_field(name="⚡ Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ Total XP", value=f"**{user.xp:,}**", inline=True)
        embed.add_field(
            name=f"Level {level} → {level+1}",
            value=f"`{xp_bar}` **{xp_in_level}/{xp_needed}** XP",
            inline=False,
        )
        embed.set_footer(text="BROski Life Engine • Earn XP by chatting, focusing & completing quests")
        await interaction.followup.send(embed=embed)

    # ─── XP Leaderboard ───────────────────────────────────────────

    @app_commands.command(name="xp_leaderboard", description="Top 10 members by XP and level")
    async def xp_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        async with get_db_session() as session:
            result = await session.execute(
                select(User).order_by(User.xp.desc()).limit(10)
            )
            top_users = result.scalars().all()

        if not top_users:
            await interaction.followup.send("No users tracked yet!")
            return

        embed = discord.Embed(title="🏆 XP Leaderboard", color=0xf1c40f)
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, u in enumerate(top_users):
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            level = level_from_xp(u.xp)
            member = interaction.guild.get_member(u.id)
            name = member.display_name if member else u.username
            lines.append(f"{medal} **{name}** — Level {level} · {u.xp:,} XP")

        embed.description = "\n".join(lines)
        embed.set_footer(text="XP earned from messages, focus sessions & quests")
        await interaction.followup.send(embed=embed)

    # ─── Activity Tracking (auto XP) ──────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id

        # Track message count
        self._message_counts[user_id] = self._message_counts.get(user_id, 0) + 1

        # Award XP every message
        try:
            brain = self._brain_modes.get(user_id)
            multiplier = BRAIN_MODES[brain]["xp_multiplier"] if brain else 1.0
            xp_award = int(XP_PER_MESSAGE * multiplier)

            async with get_db_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user:
                    user = User(
                        id=user_id,
                        username=message.author.name,
                        discriminator=message.author.discriminator or "0",
                    )
                    session.add(user)
                    await session.flush()

                old_xp = user.xp
                old_level = level_from_xp(old_xp)
                user.xp += xp_award
                user.total_messages += 1
                user.last_seen = datetime.now(timezone.utc)
                await session.commit()

                # Level up notification
                new_level = level_from_xp(user.xp)
                if new_level > old_level:
                    asyncio.create_task(
                        self._send_levelup(message.channel, message.author, new_level)
                    )
        except Exception as e:
            logger.error("XP award failed", user_id=user_id, error=str(e))

    async def _send_levelup(self, channel, member: discord.Member, new_level: int):
        """Send level-up notification."""
        try:
            embed = discord.Embed(
                title="⚡ LEVEL UP!",
                description=f"**{member.display_name}** reached **Level {new_level}**!",
                color=0xf1c40f,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Bonus Reward", value=f"**+{new_level * 50} BROski$**", inline=True)
            embed.set_footer(text="Keep going, BROski! 🐶♾️")
            await channel.send(embed=embed, delete_after=30)

            # Award level-up coins
            async with get_db_session() as session:
                result = await session.execute(select(User).where(User.id == member.id))
                user = result.scalar_one_or_none()
                if user and user.economy:
                    user.economy.balance += new_level * 50
                    user.economy.lifetime_earned += new_level * 50
                    session.add(Transaction(
                        user_id=member.id,
                        amount=new_level * 50,
                        type="credit",
                        category="level_up",
                        description=f"Level {new_level} reached",
                    ))
                    await session.commit()
        except Exception as e:
            logger.error("Level-up notification failed", error=str(e))

    # ─── Background Task ──────────────────────────────────────────

    @tasks.loop(minutes=30)
    async def leaderboard_refresh(self):
        """Background: log activity stats every 30 min."""
        logger.info("Life Engine heartbeat", active_brain_modes=len(self._brain_modes), active_vibes=len(self._vibes))

    @leaderboard_refresh.before_loop
    async def before_leaderboard_refresh(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(LifeEngine(bot))
