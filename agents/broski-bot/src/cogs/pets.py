import httpx
import discord
from discord import app_commands
from discord.ext import commands

from src.config.logging import get_logger
from src.config.settings import settings


logger = get_logger(__name__)


class Pets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    pet = app_commands.Group(name="pet", description="BROskiPet commands")

    @pet.command(name="status", description="Show your BROskiPet status")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        base = settings.pets_bridge_url.rstrip("/")
        url = f"{base}/pet/{discord_id}/status"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
        except Exception as e:
            logger.error("Pet status request failed", error=str(e), discord_id=discord_id, url=url)
            await interaction.followup.send("❌ Pet service is unavailable right now.", ephemeral=True)
            return

        if res.status_code == 404:
            await interaction.followup.send("🐾 No pet found yet. Mint one first.", ephemeral=True)
            return

        if res.status_code != 200:
            logger.warning("Pet status non-200", status_code=res.status_code, body=res.text)
            await interaction.followup.send("❌ Couldn’t fetch your pet status.", ephemeral=True)
            return

        data = res.json()
        name = str(data.get("name", "Unknown"))
        species = str(data.get("species", "Unknown"))
        rarity = str(data.get("rarity", "Unknown"))
        level = int(data.get("level", 1))
        xp = int(data.get("xp", 0))
        hunger = int(data.get("hunger", 0))
        energy = int(data.get("energy", 0))
        next_xp = data.get("next_evolution_xp")

        embed = discord.Embed(
            title=f"🐾 {name}",
            description=f"**{rarity}** {species}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=str(xp), inline=True)
        embed.add_field(name="Next Evolution", value="MAX" if next_xp is None else str(int(next_xp)), inline=True)
        embed.add_field(name="Hunger", value=str(hunger), inline=True)
        embed.add_field(name="Energy", value=str(energy), inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pets(bot))
