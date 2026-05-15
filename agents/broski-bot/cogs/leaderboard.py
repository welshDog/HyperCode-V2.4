"""
BROski Bot — Leaderboard Cog (Section 5 — One Door)
Commands: /top /rank
Reads from Core → GET /api/v1/broski/balance + /discord/actions
Bot is a pure render adapter.
"""
import discord
from discord import app_commands
from discord.ext import commands
from core_client import CoreClient, render_to_embed, fallback_embed, CoreError


class Leaderboard(commands.Cog):
    """XP and token leaderboard — wired to One Door."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot  = bot
        self.core = core

    def _ctx(self, interaction: discord.Interaction) -> dict:
        return {
            "user_id":        str(interaction.user.id),
            "username":       interaction.user.name,
            "guild_id":       str(interaction.guild_id) if interaction.guild_id else None,
            "channel_id":     str(interaction.channel_id),
            "interaction_id": str(interaction.id),
        }

    # ── /top ─────────────────────────────────────────────────
    @app_commands.command(name="top", description="XP leaderboard 🏆")
    @app_commands.describe(limit="How many to show (max 20)")
    async def top(self, interaction: discord.Interaction, limit: int = 10):
        await interaction.response.defer()
        try:
            resp  = await self.core.action(
                "leaderboard.xp",
                self._ctx(interaction),
                payload={"limit": max(1, min(limit, 20))},
            )
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed)

    # ── /rank ─────────────────────────────────────────────────
    @app_commands.command(name="rank", description="Your personal rank and stats 📊")
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            data  = await self.core.get_balance(str(interaction.user.id))
            embed = render_to_embed(data["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot, bot.core_client))
