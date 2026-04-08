from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    """Economy commands for token management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_path = 'database/broski_main.db'
    
    async def get_balance(self, user_id: int) -> int:
        """Get user's token balance."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT balance FROM users WHERE user_id = ?', (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def add_tokens(self, user_id: int, amount: int) -> int:
        """Add tokens to user's balance."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create user if doesn't exist
            await db.execute(
                '''INSERT OR IGNORE INTO users (user_id, balance, daily_streak, last_daily)
                   VALUES (?, 0, 0, NULL)''',
                (user_id,)
            )
            # Add tokens
            await db.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            await db.commit()
            return await self.get_balance(user_id)
    
    @app_commands.command(name="balance", description="Check your BROski$ token balance")
    async def balance(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        """Check token balance."""
        target_user = user or interaction.user
        
        try:
            balance = await self.get_balance(target_user.id)
            
            embed = discord.Embed(
                title="💰 BROski$ Balance",
                description=f"{target_user.mention} has **{balance:,}** BROski$ tokens",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Balance checked for {target_user.name}: {balance}")
        
        except Exception as e:
            logger.error(f"Balance command failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to check balance. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="daily", description="Claim your daily BROski$ reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        """Claim daily reward with streak bonuses."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get current streak info
                async with db.execute(
                    'SELECT daily_streak, last_daily FROM users WHERE user_id = ?',
                    (interaction.user.id,)
                ) as cursor:
                    row = await cursor.fetchone()
                
                now = datetime.utcnow()
                base_reward = 50
                streak = 0
                
                if row and row[1]:
                    last_daily = datetime.fromisoformat(row[1])
                    hours_since = (now - last_daily).total_seconds() / 3600
                    
                    if hours_since < 24:
                        # Already claimed today
                        hours_left = 24 - hours_since
                        embed = discord.Embed(
                            title="⏰ Daily Reward Already Claimed",
                            description=f"Come back in **{hours_left:.1f}** hours!",
                            color=discord.Color.orange(),
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    
                    # Check streak
                    if hours_since < 48:
                        streak = row[0] + 1
                    else:
                        streak = 1
                else:
                    streak = 1
                
                # Calculate reward with streak bonus
                streak_bonus = min(streak * 10, 100)
                total_reward = base_reward + streak_bonus
                
                # Update database
                await db.execute(
                    '''INSERT OR REPLACE INTO users (user_id, balance, daily_streak, last_daily)
                       VALUES (?, COALESCE((SELECT balance FROM users WHERE user_id = ?), 0) + ?, ?, ?)''',
                    (interaction.user.id, interaction.user.id, total_reward, streak, now.isoformat())
                )
                await db.commit()
            
            # Create embed
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                color=discord.Color.green(),
            )
            embed.add_field(name="💰 Base Reward", value=f"{base_reward} BROski$", inline=True)
            embed.add_field(name="🔥 Streak Bonus", value=f"+{streak_bonus} BROski$", inline=True)
            embed.add_field(name="📊 Total", value=f"**{total_reward} BROski$**", inline=True)
            embed.add_field(name="🔥 Streak", value=f"{streak} days", inline=False)
            embed.set_footer(text="Come back tomorrow to continue your streak!")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Daily claimed by {interaction.user.name}: {total_reward} tokens, {streak} day streak")
        
        except Exception as e:
            logger.error(f"Daily command failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to claim daily reward. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="give", description="Gift BROski$ tokens to another user")
    async def give(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ) -> None:
        """Transfer tokens to another user."""
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't give tokens to yourself!", ephemeral=True)
            return
        
        try:
            sender_balance = await self.get_balance(interaction.user.id)
            
            if sender_balance < amount:
                embed = discord.Embed(
                    title="❌ Insufficient Balance",
                    description=f"You need **{amount:,}** BROski$ but only have **{sender_balance:,}**",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            async with aiosqlite.connect(self.db_path) as db:
                # Remove from sender
                await db.execute(
                    'UPDATE users SET balance = balance - ? WHERE user_id = ?',
                    (amount, interaction.user.id)
                )
                # Add to recipient
                await db.execute(
                    '''INSERT INTO users (user_id, balance) VALUES (?, ?)
                       ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?''',
                    (user.id, amount, amount)
                )
                await db.commit()
            
            new_sender_balance = await self.get_balance(interaction.user.id)
            new_recipient_balance = await self.get_balance(user.id)
            
            embed = discord.Embed(
                title="💸 Tokens Transferred",
                description=f"{interaction.user.mention} gave **{amount:,}** BROski$ to {user.mention}",
                color=discord.Color.blue(),
            )
            embed.add_field(name=f"{interaction.user.name}'s Balance", value=f"**{new_sender_balance:,}**", inline=True)
            embed.add_field(name=f"{user.name}'s Balance", value=f"**{new_recipient_balance:,}**", inline=True)
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} gave {amount} tokens to {user.name}")
        
        except Exception as e:
            logger.error(f"Give command failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to transfer tokens. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="leaderboard", description="View top BROski$ earners")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """Display token leaderboard."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10'
                ) as cursor:
                    top_users = await cursor.fetchall()
            
            if not top_users:
                await interaction.response.send_message(
                    "No leaderboard data available yet!",
                    ephemeral=True,
                )
                return
            
            embed = discord.Embed(
                title="🏆 BROski$ Leaderboard",
                description="Top 10 token earners",
                color=discord.Color.gold(),
            )
            
            medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
            
            for idx, (user_id, balance) in enumerate(top_users):
                try:
                    user = await self.bot.fetch_user(user_id)
                    embed.add_field(
                        name=f"{medals[idx]} #{idx + 1} {user.name}",
                        value=f"**{balance:,}** BROski$",
                        inline=False,
                    )
                except:
                    embed.add_field(
                        name=f"{medals[idx]} #{idx + 1} Unknown User",
                        value=f"**{balance:,}** BROski$",
                        inline=False,
                    )
            
            await interaction.response.send_message(embed=embed)
            logger.info("Leaderboard displayed")
        
        except Exception as e:
            logger.error(f"Leaderboard command failed: {e}")
            await interaction.response.send_message(
                "❌ Failed to load leaderboard. Please try again.",
                ephemeral=True,
            )

async def setup(bot: commands.Bot) -> None:
    """Add economy cog to bot."""
    await bot.add_cog(Economy(bot))
