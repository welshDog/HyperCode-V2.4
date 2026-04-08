import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import logging

logger = logging.getLogger(__name__)

class Community(commands.Cog):
    """Community features for server engagement."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = 'database/broski_main.db'
    
    async def cog_load(self):
        """Initialize community database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS server_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    title TEXT,
                    description TEXT,
                    reward INTEGER DEFAULT 0,
                    created_at TEXT,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS event_participants (
                    event_id INTEGER,
                    user_id INTEGER,
                    joined_at TEXT,
                    PRIMARY KEY (event_id, user_id)
                )
            ''')
            await db.commit()
            logger.info("Community system initialized")
    
    @app_commands.command(name="events", description="View active community events")
    async def events(self, interaction: discord.Interaction):
        """Display active server events."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT event_id, title, description, reward
                    FROM server_events
                    WHERE guild_id = ? AND active = 1
                ''', (interaction.guild_id,)) as cursor:
                    events = await cursor.fetchall()
            
            if not events:
                embed = discord.Embed(
                    title="🎉 Community Events",
                    description="No active events right now!\nCheck back soon for challenges and rewards!",
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="🎉 Active Community Events",
                    color=discord.Color.orange()
                )
                
                for event_id, title, desc, reward in events:
                    embed.add_field(
                        name=f"🎯 {title}",
                        value=f"{desc}\n**Reward:** {reward} BROski$",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Events viewed by {interaction.user.name}")
        
        except Exception as e:
            logger.error(f"Events command failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to load events.",
                ephemeral=True
            )
    
    @app_commands.command(name="serverrank", description="Your rank in this server")
    async def server_rank(self, interaction: discord.Interaction):
        """Show user's server ranking."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get user's balance
                async with db.execute(
                    'SELECT balance FROM users WHERE user_id = ?',
                    (interaction.user.id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    user_balance = result[0] if result else 0
                
                # Get rank
                async with db.execute(
                    'SELECT COUNT(*) FROM users WHERE balance > ?',
                    (user_balance,)
                ) as cursor:
                    result = await cursor.fetchone()
                    rank = result[0] + 1
                
                # Get total users
                async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                    result = await cursor.fetchone()
                    total_users = result[0]
            
            # Calculate percentile
            percentile = 100 - ((rank / max(total_users, 1)) * 100)
            
            embed = discord.Embed(
                title=f"📊 {interaction.user.name}'s Server Rank",
                color=discord.Color.blue()
            )
            embed.add_field(name="🏆 Rank", value=f"#{rank} of {total_users}", inline=True)
            embed.add_field(name="💰 Balance", value=f"{user_balance:,} BROski$", inline=True)
            embed.add_field(name="📈 Percentile", value=f"Top {100-percentile:.1f}%", inline=True)
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Server rank checked by {interaction.user.name}")
        
        except Exception as e:
            logger.error(f"Server rank failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to get rank.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Add community cog to bot."""
    await bot.add_cog(Community(bot))
