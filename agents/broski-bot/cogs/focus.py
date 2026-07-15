"""
BROski Bot — Focus Cog (Layer 3.5)
Commands: /focus (start|stop) /focusstats
"""
import discord
from discord import app_commands
from discord.ext import commands
from core_client import CoreClient, CoreError, fallback_embed, render_to_embed


class Focus(commands.Cog):
    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core

    def _ctx(self, interaction: discord.Interaction) -> dict:
        return {
            "user_id": str(interaction.user.id),
            "username": interaction.user.name,
            "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
            "channel_id": str(interaction.channel_id),
            "interaction_id": str(interaction.id),
        }

    @app_commands.command(name="focus", description="Start or stop a focus session 🎯")
    @app_commands.describe(action="start or stop")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="start", value="start"),
            app_commands.Choice(name="stop", value="stop"),
        ]
    )
    async def focus(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        try:
            req_action = "focus.start" if action == "start" else "focus.stop"
            resp = await self.core.action(req_action, self._ctx(interaction))
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="focusstats", description="See your focus stats 📊")
    async def focusstats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            resp = await self.core.action("focus.stats", self._ctx(interaction))
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Focus(bot, bot.core_client))

