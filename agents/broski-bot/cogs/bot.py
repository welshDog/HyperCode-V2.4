"""
BROski Bot — Main Entry Point (Section 5)
HyperCode-V2.4 | agents/broski-bot/cogs/bot.py

Architecture: Bot is a pure UI adapter.
  CoreClient is the single bridge to hypercode-core.
  Cogs receive core via bot.core_client injection.
"""
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from core_client import CoreClient

load_dotenv()

def _read_secret_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


TOKEN = (
    os.getenv("DISCORD_TOKEN")
    or os.getenv("DISCORD_BOT_TOKEN")
    or _read_secret_file(os.getenv("DISCORD_TOKEN_FILE", "/run/secrets/discord_token"))
    or _read_secret_file(os.getenv("DISCORD_BOT_TOKEN_FILE", ""))
    or _read_secret_file("secrets/discord_token.txt")
)
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

intents                 = discord.Intents.default()
intents.members         = True
intents.message_content = True

bot                = commands.Bot(command_prefix="!", intents=intents)
bot.core_client    = CoreClient()    # one client, shared across all cogs

COGS = [
    "cogs.welcome",
    "cogs.economy",
    "cogs.leaderboard",
    "cogs.ai",
    "cogs.focus",
    "cogs.health_check",
    "cogs.health_history",
]


@bot.event
async def on_ready():
    print(f"\n⚡ BROski Bot ALIVE — {bot.user} (ID: {bot.user.id})")
    print(f"   Guilds: {len(bot.guilds)}")
    print(f"   CoreClient → {os.getenv('HYPERCODE_API_URL', 'http://localhost:8000')}")

    if GUILD_ID:
        guild  = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"   ✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    else:
        synced = await bot.tree.sync()
        print(f"   ✅ Synced {len(synced)} slash commands globally")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the HyperFocus Zone 🧠⚡"
        )
    )
    print("🔥 BROski Power Level: MAXIMUM\n")


async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"   ✅ {cog}")
        except Exception as e:
            print(f"   ❌ {cog}: {e}")


async def on_shutdown():
    await bot.core_client.close()


async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
