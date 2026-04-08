"""
Economy cog providing token economy commands.
Handles balance, daily rewards, transfers, and leaderboards.
"""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.config.logging import get_logger
from src.core.database import db
from src.core.exceptions import (
    DailyLimitExceededException,
    InsufficientBalanceException,
    InvalidAmountException,
)
from src.services import EconomyService

logger = get_logger(__name__)


class Economy(commands.Cog):
    """Economy commands for token management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize economy cog.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="balance", description="Check your BROski$ token balance")
    async def balance(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        """
        Check token balance.
        
        Args:
            interaction: Discord interaction
            user: Optional user to check (defaults to command author)
        """
        target_user = user or interaction.user
        
        try:
            async with db.session() as session:
                service = EconomyService(session)
                balance = await service.get_balance(target_user.id)
            
            embed = discord.Embed(
                title="💰 BROski$ Balance",
                description=f"{target_user.mention} has **{balance:,}** BROski$ tokens",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(
                "Balance checked",
                user_id=interaction.user.id,
                target_user_id=target_user.id,
                balance=balance,
            )
        
        except Exception as e:
            logger.error(
                "Balance command failed",
                user_id=interaction.user.id,
                error=str(e),
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ Failed to check balance. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="daily", description="Claim your daily BROski$ reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        """
        Claim daily reward with streak bonuses.
        
        Args:
            interaction: Discord interaction
        """
        try:
            async with db.session() as session:
                service = EconomyService(session)
                reward, streak, is_new_streak = await service.claim_daily_reward(
                    interaction.user.id,
                    interaction.user.name,
                    interaction.user.discriminator,
                )
            
            # Create embed
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                color=discord.Color.green(),
            )
            
            embed.add_field(
                name="💰 Tokens Earned",
                value=f"**+{reward:,}** BROski$",
                inline=True,
            )
            
            embed.add_field(
                name="🔥 Current Streak",
                value=f"**{streak}** days",
                inline=True,
            )
            
            if is_new_streak and streak > 1:
                embed.add_field(
                    name="⚠️ Streak Status",
                    value="Streak broken! Starting fresh.",
                    inline=False,
                )
            elif streak >= 7:
                embed.add_field(
                    name="🏆 Achievement",
                    value=f"Amazing! {streak} day streak!",
                    inline=False,
                )
            
            embed.set_footer(text="Come back tomorrow to continue your streak!")
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(
                "Daily reward claimed",
                user_id=interaction.user.id,
                reward=reward,
                streak=streak,
            )
        
        except DailyLimitExceededException as e:
            hours_remaining = 24 - ((e.details.get("retry_after", 86400)) / 3600)
            
            embed = discord.Embed(
                title="⏰ Daily Reward Already Claimed",
                description=f"You've already claimed your daily reward!\nCome back in **{hours_remaining:.1f}** hours.",
                color=discord.Color.orange(),
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(
                "Daily command failed",
                user_id=interaction.user.id,
                error=str(e),
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ Failed to claim daily reward. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="give", description="Gift BROski$ tokens to another user")
    @app_commands.describe(
        user="The user to give tokens to",
        amount="Amount of tokens to give",
    )
    async def give(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ) -> None:
        """
        Transfer tokens to another user.
        
        Args:
            interaction: Discord interaction
            user: Recipient user
            amount: Amount to transfer
        """
        try:
            async with db.session() as session:
                service = EconomyService(session)
                sender_balance, recipient_balance = await service.transfer_tokens(
                    interaction.user.id,
                    user.id,
                    amount,
                )
            
            embed = discord.Embed(
                title="💸 Tokens Transferred",
                description=f"{interaction.user.mention} gave **{amount:,}** BROski$ to {user.mention}",
                color=discord.Color.blue(),
            )
            
            embed.add_field(
                name=f"{interaction.user.name}'s Balance",
                value=f"**{sender_balance:,}** BROski$",
                inline=True,
            )
            
            embed.add_field(
                name=f"{user.name}'s Balance",
                value=f"**{recipient_balance:,}** BROski$",
                inline=True,
            )
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(
                "Tokens transferred",
                from_user_id=interaction.user.id,
                to_user_id=user.id,
                amount=amount,
            )
        
        except InvalidAmountException as e:
            await interaction.response.send_message(
                f"❌ {e.message}",
                ephemeral=True,
            )
        
        except InsufficientBalanceException as e:
            embed = discord.Embed(
                title="❌ Insufficient Balance",
                description=f"You need **{e.details['required']:,}** BROski$ but only have **{e.details['available']:,}**",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(
                "Give command failed",
                user_id=interaction.user.id,
                error=str(e),
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ Failed to transfer tokens. Please try again.",
                ephemeral=True,
            )
    
    @app_commands.command(name="leaderboard", description="View top BROski$ earners")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """
        Display token leaderboard.
        
        Args:
            interaction: Discord interaction
        """
        try:
            async with db.session() as session:
                from src.repositories import EconomyRepository
                repo = EconomyRepository(session)
                top_users = await repo.get_leaderboard(limit=10)
            
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
            
            for idx, economy in enumerate(top_users):
                user = await self.bot.fetch_user(economy.user_id)
                embed.add_field(
                    name=f"{medals[idx]} #{idx + 1} {user.name}",
                    value=f"**{economy.balance:,}** BROski$",
                    inline=False,
                )
            
            await interaction.response.send_message(embed=embed)
            
            logger.info("Leaderboard displayed", user_id=interaction.user.id)
        
        except Exception as e:
            logger.error(
                "Leaderboard command failed",
                user_id=interaction.user.id,
                error=str(e),
                exc_info=True,
            )
            await interaction.response.send_message(
                "❌ Failed to load leaderboard. Please try again.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """
    Add economy cog to bot.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(Economy(bot))
