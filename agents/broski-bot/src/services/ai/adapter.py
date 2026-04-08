"""
Adaptive NPC Behavior Service.
Modifies bot responses and interactions based on user context.
"""

from src.config.logging import get_logger
from src.core.schemas import UserProfile

logger = get_logger(__name__)


class BehaviorAdapter:
    """
    Modifies bot personality and quest descriptions based on user style.
    """
    
    def __init__(self):
        self.personalities = {
            "encouraging": {
                "greeting": "Hey BROski! You got this!",
                "quest_intro": "Here's a challenge to push you further.",
                "completion": "Amazing work! Keep it up!",
            },
            "strict": {
                "greeting": "Focus. Discipline. Execute.",
                "quest_intro": "Your next task requires precision.",
                "completion": "Acceptable performance. Next.",
            },
            "playful": {
                "greeting": "Yo! Ready to crush some goals?",
                "quest_intro": "Let's turn this into a game!",
                "completion": "Level up! That was epic!",
            },
        }
        logger.info("BehaviorAdapter initialized")

    async def adapt_response(self, user_profile: UserProfile, context: str) -> str:
        """
        Adapt bot response based on user profile.
        
        Args:
            user_profile: The user's profile.
            context: The context of the interaction (greeting, quest_intro, completion).
            
        Returns:
            Adapted response string.
        """
        # Simple logic: Determine personality based on user stats
        personality_key = "playful"  # Default
        
        if user_profile.level > 10:
            personality_key = "strict"  # High-level users get stricter feedback
        elif user_profile.total_messages < 50:
            personality_key = "encouraging"  # New users get encouragement
            
        personality = self.personalities.get(personality_key, self.personalities["playful"])
        response = personality.get(context, "Ready when you are.")
        
        logger.debug(
            "Adapted response",
            user_id=user_profile.id,
            personality=personality_key,
            context=context
        )
        return response

    async def adapt_quest_description(self, user_profile: UserProfile, original_description: str) -> str:
        """
        Modify quest description to match user's preferred tone.
        """
        intro = await self.adapt_response(user_profile, "quest_intro")
        return f"{intro} {original_description}"
