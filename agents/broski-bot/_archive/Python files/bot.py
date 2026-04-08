#!/usr/bin/env python3
"""
BROski Bot v3.0 - The Legendary Edition
Neurodivergent-friendly Discord automation empire
Author: Lyndz Williams (@welshDog)
"""

import discord
from discord.ext import commands
import aiosqlite
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/broski_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BROski')

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=['!', 'broski ', 'BROski '],
    intents=intents,
    case_insensitive=True,
    help_command=None
)

# Database path
DB_PATH = os.getenv('DB_PATH', 'database/broski_main.db')

class BROskiBot:
    """Main bot controller"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.commands_used = 0
        self.tokens_distributed = 0

    async def setup_database(self):
        """Initialize database with schema"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    broski_tokens INTEGER DEFAULT 100,
                    hyper_gems INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    last_checkin DATE,
                    cosmic_rank TEXT DEFAULT 'Neuro_Friend',
                    total_xp INTEGER DEFAULT 0,
                    total_focus_min INTEGER DEFAULT 0,
                    achievements TEXT DEFAULT '[]',
                    wallet_address TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy_transactions (
                    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT,
                    amount INTEGER,
                    direction TEXT CHECK(direction IN ('earn','spend')),
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT,
                    project_name TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_min INTEGER,
                    tokens_earned INTEGER,
                    completed BOOLEAN DEFAULT FALSE
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT,
                    quest_type TEXT,
                    quest_data TEXT,
                    status TEXT DEFAULT 'active',
                    reward_tokens INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            await db.commit()
        logger.info("✅ Database initialized successfully")

broski_controller = BROskiBot()

@bot.event
async def on_ready():
    """Bot startup event"""
    logger.info(f"🐶♾️ BROski Bot ONLINE | {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"📊 Connected to {len(bot.guilds)} servers")

    # Setup database
    Path('database').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    await broski_controller.setup_database()

    # Load all cogs
    cogs_to_load = [
        'cogs.economy',
        'cogs.focus_engine',
        'cogs.quest_system',
        'cogs.community',
        'cogs.ai_relay'
    ]

    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")

    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the Hyperfocus Zone 🐶♾️"
        )
    )

@bot.event
async def on_message(message):
    """Message event - auto-earning + command processing"""
    if message.author.bot:
        return

    # Process commands first
    await bot.process_commands(message)

@bot.hybrid_command(name="broski", description="Get BROski Bot info")
async def broski_info(ctx):
    """Main info command"""
    uptime = datetime.utcnow() - broski_controller.start_time
    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"

    embed = discord.Embed(
        title="🐶♾️ BROski Bot v3.0 - The Legendary Edition",
        description="Neurodivergent-friendly Discord automation empire",
        color=0x9b59b6
    )
    embed.add_field(name="🕐 Uptime", value=uptime_str, inline=True)
    embed.add_field(name="📊 Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="⚡ Commands Used", value=broski_controller.commands_used, inline=True)
    embed.add_field(name="💰 Tokens Distributed", value=f"{broski_controller.tokens_distributed:,} BROski$", inline=True)
    embed.add_field(
        name="🎯 Core Features",
        value="💰 Token Economy\n🎮 Quest System\n⏱️ Focus Sessions\n🤖 AI Assistance\n🏆 Achievements",
        inline=False
    )
    embed.set_footer(text="Built with 🧠 by Lyndz Williams | Welsh Indie Dev")
    embed.timestamp = datetime.utcnow()

    await ctx.send(embed=embed)
    broski_controller.commands_used += 1

@bot.hybrid_command(name="help", description="Get help with BROski Bot commands")
async def help_command(ctx):
    """Custom help command"""
    embed = discord.Embed(
        title="🐶♾️ BROski Bot - Command Guide",
        description="All available commands (use ! or / prefix)",
        color=0x3498db
    )

    embed.add_field(
        name="💰 Economy",
        value="`/balance` - Check your BROski$ tokens\n"
              "`/daily` - Claim daily reward (streak bonus!)\n"
              "`/give @user amount` - Gift tokens\n"
              "`/leaderboard` - Top earners",
        inline=False
    )

    embed.add_field(
        name="🎯 Quests & Focus",
        value="`/focus start` - Begin hyperfocus session\n"
              "`/focus end` - End session (earn +200 BROski$!)\n"
              "`/quests` - View active quests\n"
              "`/achievements` - Your unlocked achievements",
        inline=False
    )

    embed.add_field(
        name="🤖 AI & Community",
        value="`/ask` - Ask BROski AI anything\n"
              "`/profile` - Your full stats\n"
              "`/shop` - Browse purchasable items",
        inline=False
    )

    embed.set_footer(text="Made for neurodivergent brains 🧠 | ADHD + Dyslexia friendly")

    await ctx.send(embed=embed)

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not found in .env file!")
        exit(1)

    logger.info("🚀 Starting BROski Bot...")
    bot.run(TOKEN)
