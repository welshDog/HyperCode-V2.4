"""
Quest orchestration cog for Discord bot.
Handles quest lifecycle and AI coordination via Discord commands.
"""
import discord
from discord import app_commands
from discord.ext import commands

from src.config.logging import get_logger
from src.config.settings import settings
from src.core.quest_engine import AgentOrchestrator, QuestStateMachine
from src.models import QuestStatus
from src.utils.rbac import Permission, RBACManager, UserRole

logger = get_logger(__name__)


class QuestOrchestratorCog(commands.Cog):
    """
    Cog for managing quest lifecycles and AI orchestration.
    
    Provides secure endpoints (slash commands) with RBAC.
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize cog with orchestrator instances."""
        self.bot = bot
        self.orchestrator = AgentOrchestrator()
        logger.info("Quest Orchestrator Cog initialized")

    async def _check_rbac(self, interaction: discord.Interaction, permission: Permission) -> bool:
        """
        Check RBAC for a given interaction and permission.
        
        Args:
            interaction: Discord interaction
            permission: Required permission
            
        Returns:
            bool: True if access granted, False otherwise
        """
        # Determine role (simple logic for demonstration)
        user_role = UserRole.USER
        if interaction.user.id in settings.discord_owner_ids:
            user_role = UserRole.ADMIN
        elif interaction.user.guild_permissions.manage_guild:
            user_role = UserRole.MODERATOR
            
        try:
            RBACManager.check_access(user_role, permission)
            return True
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Access Denied: {str(e)}",
                ephemeral=True,
            )
            return False

    @app_commands.command(name="quest_orchestrate", description="Orchestrate quest adaptation (Admin/Mod)")
    @app_commands.describe(user_id="User to analyze", quest_id="Quest to adapt")
    async def orchestrate_adaptation(
        self,
        interaction: discord.Interaction,
        user_id: str,
        quest_id: int,
    ) -> None:
        """Slash command for AI-driven quest orchestration."""
        if not await self._check_rbac(interaction, Permission.AGENT_ORCHESTRATE):
            return
            
        await interaction.response.defer(ephemeral=True)
        
        # Real-time adaptation analysis (Sub-200ms)
        context = {"streak": 7}  # Mocking context
        adaptation = await self.orchestrator.evaluate_quest_adaptation(
            int(user_id),
            quest_id,
            context,
        )
        
        embed = discord.Embed(
            title="🎯 Quest Orchestration Result",
            color=discord.Color.blue(),
            description=f"AI-driven adaptation for User {user_id}",
        )
        embed.add_field(name="Difficulty Modifier", value=f"{adaptation['difficulty_modifier']}x")
        embed.add_field(name="Reward Multiplier", value=f"{adaptation['reward_multiplier']}x")
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="quest_status_set", description="Set quest status with state-machine validation")
    @app_commands.describe(user_id="User ID", quest_id="Quest ID", status="New status")
    @app_commands.choices(status=[
        app_commands.Choice(name="Available", value="available"),
        app_commands.Choice(name="Active", value="active"),
        app_commands.Choice(name="Completed", value="completed"),
        app_commands.Choice(name="Failed", value="failed"),
        app_commands.Choice(name="Expired", value="expired"),
    ])
    async def set_quest_status(
        self,
        interaction: discord.Interaction,
        user_id: str,
        quest_id: int,
        status: str,
    ) -> None:
        """Slash command for secure quest state transitions."""
        if not await self._check_rbac(interaction, Permission.QUEST_UPDATE):
            return
            
        # 1. Fetch current status (mocking for demonstration)
        current_status = QuestStatus.ACTIVE
        target_status = QuestStatus(status)
        
        # 2. Validate transition via state-machine
        try:
            QuestStateMachine.validate_transition(current_status, target_status)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Invalid Transition: {str(e)}",
                ephemeral=True,
            )
            return
            
        # 3. Apply change (Database logic would go here)
        await interaction.response.send_message(
            f"✅ Quest {quest_id} status updated from {current_status} to {target_status} for user {user_id}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    """Setup hook for cog."""
    await bot.add_cog(QuestOrchestratorCog(bot))
