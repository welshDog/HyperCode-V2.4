import httpx
import discord
from discord import app_commands
from discord.ext import commands

from src.config.logging import get_logger
from src.config.settings import settings
from src.core.database import db
from src.core.exceptions import InsufficientBalanceException
from src.repositories import UserRepository
from src.services import EconomyService


logger = get_logger(__name__)


class Pets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    pet = app_commands.Group(name="pet", description="BROskiPet commands")

    async def _bridge_get(self, path: str, timeout_s: float = 15.0) -> httpx.Response:
        base = settings.pets_bridge_url.rstrip("/")
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            return await client.get(f"{base}{path}")

    async def _bridge_post(self, path: str, json_body: dict, timeout_s: float = 45.0) -> httpx.Response:
        base = settings.pets_bridge_url.rstrip("/")
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            return await client.post(f"{base}{path}", json=json_body)

    @pet.command(name="status", description="Show your BROskiPet status")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)

        try:
            res = await self._bridge_get(f"/pet/{discord_id}/status")
        except Exception as e:
            logger.error("Pet status request failed", error=str(e), discord_id=discord_id)
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

    @pet.command(name="chat", description="Chat with your BROskiPet")
    async def chat(self, interaction: discord.Interaction, message: str) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        try:
            res = await self._bridge_post(
                f"/pet/{discord_id}/chat",
                {"message": message, "mode": "chat"},
                timeout_s=180.0,
            )
        except Exception as e:
            logger.error("Pet chat request failed", error=str(e), discord_id=discord_id)
            await interaction.followup.send("❌ Pet service is unavailable right now.", ephemeral=True)
            return

        if res.status_code == 404:
            await interaction.followup.send("🐾 No pet found yet. Mint one first.", ephemeral=True)
            return
        if res.status_code != 200:
            await interaction.followup.send("❌ Couldn’t chat with your pet right now.", ephemeral=True)
            return

        data = res.json()
        reply = str(data.get("reply", "")).strip() or "…"
        pet = data.get("pet") or {}
        name = str(pet.get("name", "BROskiPet"))

        embed = discord.Embed(
            title=f"🐾 {name}",
            description=reply[:3800],
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @pet.command(name="ask", description="Ask your BROskiPet for coding help")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        try:
            res = await self._bridge_post(
                f"/pet/{discord_id}/chat",
                {"message": question, "mode": "ask"},
                timeout_s=180.0,
            )
        except Exception as e:
            logger.error("Pet ask request failed", error=str(e), discord_id=discord_id)
            await interaction.followup.send("❌ Pet service is unavailable right now.", ephemeral=True)
            return

        if res.status_code == 404:
            await interaction.followup.send("🐾 No pet found yet. Mint one first.", ephemeral=True)
            return
        if res.status_code != 200:
            await interaction.followup.send("❌ Couldn’t fetch an answer right now.", ephemeral=True)
            return

        data = res.json()
        reply = str(data.get("reply", "")).strip() or "…"
        pet = data.get("pet") or {}
        name = str(pet.get("name", "BROskiPet"))

        embed = discord.Embed(
            title=f"🧠 {name} (Code Help)",
            description=reply[:3800],
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @pet.command(name="powers", description="List your pet's powers")
    async def powers(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        try:
            res = await self._bridge_get(f"/pet/{discord_id}/powers")
        except Exception as e:
            logger.error("Pet powers request failed", error=str(e), discord_id=discord_id)
            await interaction.followup.send("❌ Pet service is unavailable right now.", ephemeral=True)
            return

        if res.status_code == 404:
            await interaction.followup.send("🐾 No pet found yet. Mint one first.", ephemeral=True)
            return
        if res.status_code != 200:
            await interaction.followup.send("❌ Couldn’t fetch powers right now.", ephemeral=True)
            return

        data = res.json()
        species = str(data.get("species", "Unknown"))
        power = str(data.get("power", "")).strip() or "Unknown"
        stage = int(data.get("stage", 1))
        unlocked = data.get("unlocked") or []
        caps = data.get("capabilities") or []

        embed = discord.Embed(
            title=f"⚡ {species} Powers",
            description=f"Stage **{stage}**",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Power", value=power, inline=False)
        embed.add_field(name="Unlocked", value=", ".join([str(x) for x in unlocked]) or "none", inline=False)
        if caps:
            embed.add_field(name="Capabilities", value=", ".join([str(x) for x in caps])[:1000], inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @pet.command(name="feed", description="Feed your pet (costs 10 BROski$)")
    async def feed(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        user_id = int(interaction.user.id)
        username = str(interaction.user.name)
        discriminator = str(getattr(interaction.user, "discriminator", "0"))

        try:
            async with db.session() as session:
                user_repo = UserRepository(session)
                await user_repo.get_or_create(user_id, username, discriminator)
                service = EconomyService(session)
                await service.process_transaction(
                    user_id=user_id,
                    amount=10,
                    type="debit",
                    category="pet_feed",
                    description="Fed BROskiPet",
                )
        except InsufficientBalanceException:
            await interaction.followup.send("❌ Not enough BROski$ to feed your pet (need 10).", ephemeral=True)
            return
        except Exception as e:
            logger.error("Pet feed debit failed", error=str(e), user_id=user_id)
            await interaction.followup.send("❌ Couldn’t spend BROski$ right now.", ephemeral=True)
            return

        discord_id = str(interaction.user.id)
        try:
            res = await self._bridge_post(f"/pet/{discord_id}/feed", {"spent_broski": 10})
        except Exception as e:
            logger.error("Pet feed request failed", error=str(e), discord_id=discord_id)
            await interaction.followup.send("❌ Pet service is unavailable right now.", ephemeral=True)
            return

        if res.status_code == 404:
            await interaction.followup.send("🐾 No pet found yet. Mint one first.", ephemeral=True)
            return
        if res.status_code != 200:
            await interaction.followup.send("❌ Couldn’t feed your pet right now.", ephemeral=True)
            return

        data = res.json()
        hunger = int(data.get("hunger", 0))
        energy = int(data.get("energy", 0))
        happiness = int(data.get("happiness", 0))

        embed = discord.Embed(
            title="🍖 Pet Fed",
            description="Your pet is happier and stronger.",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Hunger", value=f"{hunger}/100", inline=True)
        embed.add_field(name="Energy", value=f"{energy}/100", inline=True)
        embed.add_field(name="Happiness", value=f"{happiness}/100", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @pet.command(name="leaderboard", description="Show the top BROskiPets by XP")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=False)

        try:
            res = await self._bridge_get("/leaderboard")
        except Exception as e:
            logger.error("Pet leaderboard request failed", error=str(e))
            await interaction.followup.send("❌ Leaderboard service is unavailable right now.", ephemeral=False)
            return

        if res.status_code != 200:
            logger.warning("Pet leaderboard non-200", status_code=res.status_code, body=res.text)
            await interaction.followup.send("❌ Couldn’t fetch leaderboard right now.", ephemeral=False)
            return

        data = res.json()
        if not isinstance(data, list) or len(data) == 0:
            await interaction.followup.send("🏆 No leaderboard entries yet. Hatch some pets first!", ephemeral=False)
            return

        lines: list[str] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            rank = int(row.get("rank", 0))
            name = str(row.get("name", "Unknown"))
            species = str(row.get("species", "Unknown"))
            level = int(row.get("level", 1))
            xp = int(row.get("xp", 0))
            prefix = "⭐ " if rank == 1 else ""
            lines.append(f"{prefix}#{rank} {name} ({species}) — Lvl {level} — {xp} XP")

        embed = discord.Embed(
            title="🏆 BROskiPets Leaderboard",
            description="\n".join(lines)[:3900],
            color=discord.Color.gold(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pets(bot))
