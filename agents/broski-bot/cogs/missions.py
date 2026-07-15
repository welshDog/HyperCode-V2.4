import discord
from discord import app_commands
from discord.ext import commands
from core_client import CoreClient, CoreError, fallback_embed, render_to_embed


class Missions(commands.Cog):
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

    @app_commands.command(name="missions", description="See today's missions 📋")
    async def missions(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            resp = await self.core.action("missions.today", self._ctx(interaction))
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="missions-claim", description="Claim today's mission reward 🏆")
    async def missions_claim(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            resp = await self.core.action(
                "missions.claim",
                self._ctx(interaction),
                payload={"slug": "focus_block"},
            )
            embed = render_to_embed(resp["render"])
        except CoreError as e:
            embed = fallback_embed(e)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Missions(bot, bot.core_client))

