import discord
from discord import app_commands
from discord.ext import commands
import logging

from src.core.database import db
from src.services.quest import QuestService
from src.services.achievement import AchievementService
from src.models import QuestStatus

logger = logging.getLogger(__name__)

class QuestSystem(commands.Cog):
    """Quest and achievement system for BROski Bot."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="quests", description="View available quests")
    async def quests(self, interaction: discord.Interaction):
        """Display available quests."""
        await interaction.response.defer()
        
        async with db.session() as session:
            service = QuestService(session)
            user_quests = await service.get_active_quests(interaction.user.id)
            
            if not user_quests:
                # Generate new quests if none active
                logger.info(f"Generating daily quests for {interaction.user.id}")
                user_quests = await service.generate_daily_quests(interaction.user.id)
            
            if not user_quests:
                await interaction.followup.send(
                    "🎯 No quests available right now! Check back soon!"
                )
                return
            
            embed = discord.Embed(
                title="🎯 BROski Quests",
                description="Complete quests to earn BROski$ tokens and unlock achievements!",
                color=discord.Color.purple()
            )
            
            difficulty_colors = {
                'easy': '🟢',
                'medium': '🟡',
                'hard': '🔴'
            }
            
            quest_type_icons = {
                'tutorial': '📚',
                'daily': '📅',
                'economy': '💰',
                'focus': '⏱️',
                'social': '👥',
                'productivity': '⚡',
            }
            
            for uq in user_quests:
                quest = uq.quest
                status = uq.status
                progress = uq.progress
                
                status_emoji = {
                    QuestStatus.AVAILABLE: '⚪',
                    QuestStatus.ACTIVE: '🔵',
                    QuestStatus.COMPLETED: '✅',
                    QuestStatus.FAILED: '❌',
                    QuestStatus.EXPIRED: '⏰'
                }.get(status, '⚪')
                
                type_icon = quest_type_icons.get(quest.category, '🎯')
                # Determine difficulty roughly by reward amount
                if quest.token_reward < 100:
                    diff_color = difficulty_colors['easy']
                elif quest.token_reward < 300:
                    diff_color = difficulty_colors['medium']
                else:
                    diff_color = difficulty_colors['hard']
                
                field_name = f"{status_emoji} {diff_color} {type_icon} {quest.title}"
                field_value = f"{quest.description}\n**Reward:** {quest.token_reward} BROski$"
                
                if status == QuestStatus.ACTIVE and progress > 0:
                    field_value += f"\n*Progress: {progress}/{quest.requirement_count}*"
                
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text="Quests update daily!")
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="completequest", description="Mark a quest as complete (for testing)")
    @app_commands.describe(quest_id="Quest ID to complete")
    async def complete_quest(self, interaction: discord.Interaction, quest_id: int):
        """Complete a quest (testing/manual completion)."""
        await interaction.response.defer(ephemeral=True)
        
        async with db.session() as session:
            service = QuestService(session)
            # Find the user_quest ID that matches this quest_id for this user
            # Assuming command input is Quest ID (from template)
            # But we track UserQuest ID internally usually.
            # Let's assume user passes Quest ID from the UI (which usually shows template ID or user_quest ID?)
            # The previous code selected by quest_id.
            
            # We need to find the active UserQuest for this quest_id
            active_quests = await service.get_active_quests(interaction.user.id)
            target_uq = next((uq for uq in active_quests if uq.quest_id == quest_id), None)
            
            if not target_uq:
                await interaction.followup.send("❌ Quest not found or not active!", ephemeral=True)
                return
            
            result = await service.complete_quest(interaction.user.id, target_uq.quest_id)
            
            if result:
                embed = discord.Embed(
                    title="🎉 Quest Completed!",
                    description=f"**{result.quest.title}**\nYou earned **{result.quest.token_reward} BROski$**!",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to complete quest.", ephemeral=True)

    @app_commands.command(name="achievements", description="View your unlocked achievements")
    async def achievements(self, interaction: discord.Interaction):
        """Display user achievements."""
        await interaction.response.defer(ephemeral=True)
        
        async with db.session() as session:
            service = AchievementService(session)
            user_achievements = await service.get_user_achievements(interaction.user.id)
            
            if not user_achievements:
                embed = discord.Embed(
                    title=f"🏆 {interaction.user.name}'s Achievements",
                    description="You haven't unlocked any achievements yet. Keep grinding!",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"🏆 {interaction.user.name}'s Achievements",
                color=discord.Color.gold()
            )
            
            for ua in user_achievements:
                ach = ua.achievement
                embed.add_field(
                    name=f"{ach.icon} {ach.name}",
                    value=f"{ach.description}\n*Unlocked: {ua.unlocked_at.strftime('%Y-%m-%d')}*",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add quest system cog to bot."""
    await bot.add_cog(QuestSystem(bot))
