"""
BROski Discord Bot - Basic Setup with Sharding
Production-ready bot skeleton with error handling and security
"""

import os
import discord
from discord.ext import commands
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env file!")

handler = RotatingFileHandler('bot.log', maxBytes=20*1024*1024, backupCount=14)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[handler, logging.StreamHandler()]
)
logger = logging.getLogger('broski_bot')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.AutoShardedBot(command_prefix="!", intents=intents, shard_count=None)

@bot.event
async def on_ready():
    logger.info(f'BROski Bot online: {bot.user}')
    logger.info(f'Guilds: {len(bot.guilds)} | Shards: {bot.shard_count}')
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers")
    )

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f'Unhandled exception in {event}', exc_info=True)

@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(f'Cooldown: {error.retry_after:.1f}s', ephemeral=True)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.respond(f'Missing: {error.missing_permissions}', ephemeral=True)
    else:
        logger.error(f'Command error: {ctx.command.name}', exc_info=error)
        await ctx.respond('An error occurred. Incident logged.', ephemeral=True)

@bot.slash_command(name="ping", description="Check bot latency")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond(f'Pong! {round(bot.latency * 1000, 2)}ms')

@bot.slash_command(name="stats", description="Show bot statistics")
async def stats(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="BROski Bot Stats", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Shards", value=bot.shard_count, inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(name="ban", description="Ban a member")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban_member(ctx: discord.ApplicationContext, member: discord.Member, reason: str = "No reason"):
    if member.top_role >= ctx.author.top_role:
        return await ctx.respond("Cannot ban equal/higher role", ephemeral=True)
    await member.ban(reason=f"{reason} | By {ctx.author}")
    logger.info(f'Ban: {member} | Guild: {ctx.guild.name} | Mod: {ctx.author}')
    await ctx.respond(f"Banned {member.mention}. Reason: {reason}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
