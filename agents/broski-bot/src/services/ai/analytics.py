"""
Predictive Analytics Service.
Analyzes user data to predict churn and optimize engagement.
"""
from typing import Optional

from src.config.logging import get_logger
from src.core.schemas import UserProfile

logger = get_logger(__name__)


class AnalyticsEngine:
    """
    Predictive analytics for user behavior.
    """
    
    def __init__(self):
        logger.info("AnalyticsEngine initialized")

    async def predict_churn(self, user_profile: UserProfile, last_activity_days: int) -> float:
        """
        Predict churn probability (0.0 - 1.0).
        
        Args:
            user_profile: The user's profile.
            last_activity_days: Days since last activity.
            
        Returns:
            Churn probability.
        """
        # Simple heuristic model
        churn_prob = 0.05  # Base probability
        
        if last_activity_days > 7:
            churn_prob += 0.3
        elif last_activity_days > 3:
            churn_prob += 0.1
            
        if user_profile.level < 5:
            churn_prob += 0.1  # New users are higher risk
            
        if user_profile.total_messages < 10:
            churn_prob += 0.2  # Low engagement users
            
        churn_prob = min(churn_prob, 1.0)
        
        logger.debug(
            "Predicted churn",
            user_id=user_profile.id,
            probability=churn_prob,
            last_activity=last_activity_days
        )
        return churn_prob

    async def suggest_retention_action(self, churn_prob: float) -> Optional[str]:
        """
        Suggest action to prevent churn based on probability.
        """
        if churn_prob > 0.7:
            return "send_reengagement_quest"  # High risk: offer special quest
        elif churn_prob > 0.4:
            return "send_notification"  # Medium risk: reminder
        
        return None  # Low risk: no action
