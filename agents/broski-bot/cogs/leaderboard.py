"""
BROski Bot — Leaderboard Cog
Commands: /top /rank
Wired to: leaderboard_top() Supabase function + broski_members XP
"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _level_from_xp(xp: int) -> int:
    if xp >= 2000: return 6
    if xp >= 1000: return 5
    if xp >= 500:  return 4
    if xp >= 250:  return 3
    if xp >= 100:  return 2
    return 1


def _rank_emoji(pos: int) -> str:
    return ["🥇", "🥈", "🥉"][pos] if pos < 3 else f"`#{pos+1}`"


class Leaderboard(commands.Cog):
    """XP and token leaderboard commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="top", description="See the XP leaderboard 🏆")
    @app_commands.describe(limit="How many to show (default 10, max 20)")
    async def top(self, interaction: discord.Interaction, limit: int = 10):
        await interaction.response.defer()
        limit = max(1, min(limit, 20))
        sb = get_supabase()
        res = sb.table("broski_members").select(
            "username,xp,level,streak_days,broski_tokens"
        ).order("xp", desc=True).limit(limit).execute()
        rows = res.data or []

        if not rows:
            await interaction.followup.send("🏜️ No members yet — be the first legend!")
            return

        lines = []
        for i, r in enumerate(rows):
            xp = r.get("xp", 0)
            lvl = _level_from_xp(xp)
            streak = r.get("streak_days", 0)
            streak_s = f" 🔥{streak}" if streak >= 3 else ""
            lines.append(
                f"{_rank_emoji(i)} **{r['username']}** — "
                f"Lv.{lvl} • {xp:,} XP{streak_s}"
            )

        embed = discord.Embed(
            title="🏆 HyperFocus Zone — XP Leaderboard",
            description="\n".join(lines),
            colour=discord.Colour.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Earn XP with /daily, /quests, and lessons!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rank", description="Check your personal rank and stats 📊")
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sb = get_supabase()
        did = str(interaction.user.id)

        res = sb.table("broski_members").select("*").eq("discord_id", did).limit(1).execute()
        row = res.data[0] if res.data else {}

        if not row:
            embed = discord.Embed(
                title="🆕 Not in the system yet!",
                description="Use `/daily` to register and start earning XP! 🚀",
                colour=discord.Colour.orange(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        xp = row.get("xp", 0)
        tokens = row.get("broski_tokens", 0)
        streak = row.get("streak_days", 0)
        level = _level_from_xp(xp)
        xp_next = level * 100
        xp_cur = xp % xp_next
        bar = "█" * int((xp_cur / xp_next) * 10) + "░" * (10 - int((xp_cur / xp_next) * 10))

        rank_res = sb.table("broski_members").select("discord_id").gte("xp", xp).execute()
        position = len(rank_res.data or [])

        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name}'s Stats",
            colour=discord.Colour.blurple(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🏆 Rank", value=f"#{position}", inline=True)
        embed.add_field(name="⚡ Level", value=str(level), inline=True)
        embed.add_field(name="🔥 Streak", value=f"{streak} days", inline=True)
        embed.add_field(name="✨ XP Progress", value=f"{bar} {xp_cur}/{xp_next}", inline=False)
        embed.add_field(name="💰 BROski$", value=f"{tokens:,} tokens", inline=True)
        embed.set_footer(text="Keep going bro — every message counts!")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
