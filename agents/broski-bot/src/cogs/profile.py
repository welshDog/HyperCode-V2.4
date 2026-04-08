"""
Profile Cog — Rich user profiles backed by PostgreSQL.

Commands:
  /profile [@member]  — View a rich profile card
  /setbio <text>      — Set your bio (max 200 chars)
  /settitle <title>   — Set a display title
  /titles             — Browse available titles
  /badges             — View your earned badges
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from sqlalchemy import select, func as sqlfunc
import logging

from src.core.database import get_db_session
from src.models import User, Economy, FocusSession, Transaction

logger = logging.getLogger(__name__)

# Title unlock requirements (level-gated)
TITLES = {
    "Newcomer": {"level": 1, "emoji": "🌱"},
    "Regular": {"level": 5, "emoji": "⭐"},
    "Dedicated": {"level": 10, "emoji": "💪"},
    "Hyperfocused": {"level": 15, "emoji": "⚡"},
    "BROski Elite": {"level": 20, "emoji": "💎"},
    "Legendary BROski": {"level": 30, "emoji": "🏆"},
    "Godlike": {"level": 50, "emoji": "🌟"},
    "The One": {"level": 100, "emoji": "♾️"},
}

XP_LEVEL_BASE = 100

def level_from_xp(xp: int) -> int:
    level = 1
    total = 0
    while True:
        needed = level * XP_LEVEL_BASE
        if total + needed > xp:
            break
        total += needed
        level += 1
    return level

def get_title_for_level(level: int) -> tuple[str, str]:
    """Return (title, emoji) for the highest unlocked title at this level."""
    best = ("Newcomer", "🌱")
    for title, data in TITLES.items():
        if level >= data["level"]:
            best = (title, data["emoji"])
    return best

# In-memory bios and custom titles (persisted across restarts only via restart = new session, acceptable for now)
_bios: dict[int, str] = {}
_custom_titles: dict[int, str] = {}


class ProfileCog(commands.Cog, name="Profile"):
    """Rich profile system for BROski World."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View a rich BROski profile card")
    @app_commands.describe(member="Member to view (default: yourself)")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()
        target = member or interaction.user
        user_id = target.id

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            # Rank by XP
            rank_result = await session.execute(
                select(sqlfunc.count(User.id)).where(User.xp > (user.xp if user else 0))
            )
            rank = (rank_result.scalar() or 0) + 1

            # Focus session count
            focus_result = await session.execute(
                select(sqlfunc.count(FocusSession.id)).where(
                    FocusSession.user_id == user_id,
                    FocusSession.is_active == False,
                )
            )
            focus_count = focus_result.scalar() or 0

        if not user:
            await interaction.followup.send(f"❌ **{target.display_name}** hasn't been seen yet — they need to send a message first!")
            return

        level = level_from_xp(user.xp)
        auto_title, auto_emoji = get_title_for_level(level)
        custom_title = _custom_titles.get(user_id)
        display_title = custom_title if custom_title else f"{auto_emoji} {auto_title}"
        bio = _bios.get(user_id, "*No bio set — use `/setbio` to add one!*")

        eco = user.economy
        balance = eco.balance if eco else 0
        streak = eco.daily_streak if eco else 0
        crystals = eco.memory_crystals if eco else 0

        rank_badge = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

        # XP progress bar
        xp_in_level = user.xp - sum(l * XP_LEVEL_BASE for l in range(1, level))
        xp_needed = level * XP_LEVEL_BASE
        bar_fill = int((xp_in_level / xp_needed) * 20) if xp_needed else 0
        xp_bar = "█" * bar_fill + "░" * (20 - bar_fill)

        embed = discord.Embed(
            title=f"{display_title}",
            description=bio,
            color=target.colour if target.colour.value != 0 else 0x9b59b6,
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="🏅 Rank", value=f"**{rank_badge}**", inline=True)
        embed.add_field(name="⚡ Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ XP", value=f"**{user.xp:,}**", inline=True)

        embed.add_field(name="💰 Balance", value=f"**{balance:,} BROski$**", inline=True)
        embed.add_field(name="🔥 Streak", value=f"**{streak}** days", inline=True)
        embed.add_field(name="💎 Crystals", value=f"**{crystals}**", inline=True)

        embed.add_field(name="💬 Messages", value=f"**{user.total_messages:,}**", inline=True)
        embed.add_field(name="⏱️ Focus Sessions", value=f"**{focus_count}**", inline=True)
        embed.add_field(name="👀 Last Seen", value=f"<t:{int(user.last_seen.timestamp())}:R>", inline=True)

        embed.add_field(
            name=f"Level Progress {level}→{level+1}",
            value=f"`{xp_bar}` {xp_in_level}/{xp_needed} XP",
            inline=False,
        )

        embed.set_footer(
            text=f"Joined BROski: {user.created_at.strftime('%d %b %Y')} • BROski Life Engine v4.0"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="setbio", description="Set your profile bio (max 200 characters)")
    @app_commands.describe(text="Your bio text")
    async def setbio(self, interaction: discord.Interaction, text: str):
        if len(text) > 200:
            await interaction.response.send_message("❌ Bio must be 200 characters or less.", ephemeral=True)
            return
        _bios[interaction.user.id] = text
        await interaction.response.send_message(f"✅ Bio updated! View it with `/profile`.", ephemeral=True)

    @app_commands.command(name="settitle", description="Set a custom display title (must be unlocked for your level)")
    @app_commands.describe(title="Title to set")
    async def settitle(self, interaction: discord.Interaction, title: str):
        await interaction.response.defer(ephemeral=True)

        if title not in TITLES:
            options = ", ".join(f"`{t}`" for t in TITLES)
            await interaction.followup.send(f"❌ Unknown title. Available: {options}")
            return

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == interaction.user.id))
            user = result.scalar_one_or_none()

        if not user:
            await interaction.followup.send("❌ No profile data yet — send a message first!")
            return

        level = level_from_xp(user.xp)
        required_level = TITLES[title]["level"]
        if level < required_level:
            await interaction.followup.send(
                f"❌ **{title}** requires Level **{required_level}**. You're Level **{level}**."
            )
            return

        emoji = TITLES[title]["emoji"]
        _custom_titles[interaction.user.id] = f"{emoji} {title}"
        await interaction.followup.send(f"✅ Title set to **{emoji} {title}**! View it with `/profile`.")

    @app_commands.command(name="titles", description="Browse all available titles and unlock requirements")
    async def titles(self, interaction: discord.Interaction):
        await interaction.response.defer()

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == interaction.user.id))
            user = result.scalar_one_or_none()

        current_level = level_from_xp(user.xp) if user else 1

        embed = discord.Embed(title="🏷️ Available Titles", color=0x9b59b6)
        lines = []
        for title, data in TITLES.items():
            unlocked = current_level >= data["level"]
            status = "✅" if unlocked else f"🔒 Lv.{data['level']}"
            lines.append(f"{data['emoji']} **{title}** — {status}")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Your level: {current_level} | Use /settitle <name> to equip")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="badges", description="View your earned badges and achievements")
    async def badges(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

        if not user:
            await interaction.followup.send("❌ No profile data yet!")
            return

        level = level_from_xp(user.xp)
        eco = user.economy
        streak = eco.max_daily_streak if eco else 0
        focus_count_result_placeholder = 0  # Would query focus sessions

        # Compute earned badges
        earned = []
        if user.total_messages >= 1:
            earned.append("💬 First Message")
        if user.total_messages >= 100:
            earned.append("📢 Chatterbox (100 msgs)")
        if user.total_messages >= 1000:
            earned.append("🎙️ Voice of the Server (1k msgs)")
        if level >= 5:
            earned.append("⭐ Rising Star (Lv. 5)")
        if level >= 10:
            earned.append("💪 Dedicated (Lv. 10)")
        if level >= 20:
            earned.append("💎 Elite (Lv. 20)")
        if level >= 50:
            earned.append("🌟 Legend (Lv. 50)")
        if streak >= 7:
            earned.append("🔥 Week Warrior (7-day streak)")
        if streak >= 30:
            earned.append("🏆 Monthly Champion (30-day streak)")
        if eco and eco.lifetime_earned >= 1000:
            earned.append("💰 Thousandaire (1k BROski$ earned)")
        if eco and eco.lifetime_earned >= 10000:
            earned.append("🏦 BROski Mogul (10k earned)")

        embed = discord.Embed(
            title=f"🎖️ {interaction.user.display_name}'s Badges",
            color=0xf1c40f,
        )
        if earned:
            embed.description = "\n".join(f"• {b}" for b in earned)
        else:
            embed.description = "No badges yet — start earning by chatting and focusing!"
        embed.set_footer(text=f"{len(earned)} badges earned | BROski Life Engine")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
