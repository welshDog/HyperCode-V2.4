"""
BROski Bot — Economy Cog (Section 5 — One Door)
Commands: /balance /daily /give /rich
All writes go via CoreClient → POST /api/v1/discord/actions
Bot is a pure render adapter. Brain decides everything.
"""
import discord
from discord import app_commands
from discord.ext import commands
from core_client import CoreClient, render_to_embed, fallback_embed, CoreError


class Economy(commands.Cog):
    """BROski$ token economy commands — wired to One Door."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot  = bot
        self.core = core

    def _ctx(self, interaction: discord.Interaction) -> dict:
        """Build discord context dict for every Core call."""
        return {
            "user_id":        str(interaction.user.id),
            "username":       interaction.user.name,
            "guild_id":       str(interaction.guild_id) if interaction.guild_id else None,
            "channel_id":     str(interaction.channel_id),
            "interaction_id": str(interaction.id),
        }

    # ── /balance ─────────────────────────────────────────────
    @app_commands.command(name="balance", description="Check your BROski$ balance 💰")
    async def balance(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            data   = await self.core.get_balance(str(interaction.user.id))
            embed  = render_to_embed(data["render"])
        except CoreError as e:
            embed  = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /daily ───────────────────────────────────────────────
    @app_commands.command(name="daily", description="Claim your daily BROski$ tokens 🌅")
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            resp  = await self.core.action("daily.claim", self._ctx(interaction))
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /give ────────────────────────────────────────────────
    @app_commands.command(name="give", description="Send BROski$ to another member 🎁")
    @app_commands.describe(member="Who to send to", amount="How many BROski$ to send")
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        try:
            resp  = await self.core.action(
                "economy.give",
                self._ctx(interaction),
                payload={"to_discord_id": str(member.id), "amount": amount},
            )
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=False)

    # ── /rich ────────────────────────────────────────────────
    @app_commands.command(name="rich", description="Top BROski$ holders 🏦")
    async def rich(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            resp  = await self.core.action("economy.leaderboard", self._ctx(interaction))
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    # CoreClient injected from bot.py
    await bot.add_cog(Economy(bot, bot.core_client))
