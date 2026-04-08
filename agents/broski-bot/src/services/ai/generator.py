"""
Dynamic Quest Generation Service.
Uses user history and preferences to generate personalized quests.
"""
from datetime import datetime, timedelta
from typing import List

from src.config.logging import get_logger
from src.core.schemas import UserProfile
from src.models import Quest

logger = get_logger(__name__)


class QuestGenerator:
    """
    Generates dynamic quests based on user profile and history.
    """
    
    def __init__(self):
        self.templates = [
            {
                "title": "Focus Master",
                "description": "Complete {count} focus sessions of at least 25 minutes.",
                "category": "productivity",
                "requirement_type": "focus_sessions",
                "base_reward": 100,
                "base_xp": 50,
            },
            {
                "title": "Social Butterfly",
                "description": "Send {count} messages in the community channels.",
                "category": "social",
                "requirement_type": "messages",
                "base_reward": 50,
                "base_xp": 25,
            },
            {
                "title": "Eco Warrior",
                "description": "Earn {count} tokens through economy activities.",
                "category": "economy",
                "requirement_type": "earn_tokens",
                "base_reward": 150,
                "base_xp": 75,
            },
        ]
        logger.info("QuestGenerator initialized")

    async def generate_quests(self, user_profile: UserProfile, count: int = 3) -> List[Quest]:
        """
        Generate a list of personalized quests for the user.
        
        Args:
            user_profile: The user's profile and stats.
            count: Number of quests to generate.
            
        Returns:
            List of generated Quest objects (not yet persisted).
        """
        generated_quests = []
        
        # Simple logic: Scale difficulty based on user level
        difficulty_multiplier = 1.0 + (user_profile.level * 0.1)
        
        for i in range(count):
            template = self.templates[i % len(self.templates)]
            
            # Dynamic requirement count
            base_count = 5
            req_count = int(base_count * difficulty_multiplier)
            
            # Dynamic rewards
            token_reward = int(template["base_reward"] * difficulty_multiplier)
            xp_reward = int(template["base_xp"] * difficulty_multiplier)
            
            quest = Quest(
                title=f"{template['title']} {['I', 'II', 'III', 'IV', 'V'][min(user_profile.level, 4)]}",
                description=template["description"].format(count=req_count),
                category=template["category"],
                requirement_type=template["requirement_type"],
                requirement_count=req_count,
                token_reward=token_reward,
                xp_reward=xp_reward,
                memory_crystal_reward=1,  # Base reward
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=1)
            )
            generated_quests.append(quest)
            
        logger.info(
            "Generated quests",
            user_id=user_profile.id,
            count=len(generated_quests),
            multiplier=difficulty_multiplier
        )
        return generated_quests
