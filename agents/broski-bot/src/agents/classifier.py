"""
AI-Powered Contribution Classification System
Analyzes Discord messages and classifies contributions for token rewards.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger

logger = get_logger(__name__)


class ContributionType(str, Enum):
    """Types of community contributions."""
    ANSWERING_QUESTION = "answering_question"
    CREATING_CONTENT = "creating_content"
    MODERATING = "moderating"
    REPORTING_ISSUE = "reporting_issue"
    CODE_CONTRIBUTION = "code_contribution"
    EVENT_PARTICIPATION = "event_participation"
    DAILY_ENGAGEMENT = "daily_engagement"
    HELPING_NEWCOMER = "helping_newcomer"
    FEEDBACK_GIVING = "feedback_giving"
    TUTORIAL_CREATING = "tutorial_creating"
    BUG_FIXING = "bug_fixing"
    COMMUNITY_SUPPORT = "community_support"


@dataclass
class ContributionScore:
    """Contribution scoring result."""
    contribution_type: ContributionType
    base_reward: int
    quality_multiplier: float
    final_reward: int
    confidence: float
    reasoning: str
    metadata: Dict[str, any]


class AIContributionClassifier:
    """
    AI-powered classifier for identifying and scoring community contributions.
    
    Uses pattern matching, NLP, and heuristics to automatically detect and
    reward valuable community interactions.
    """
    
    # Reward configuration
    REWARD_CONFIG = {
        ContributionType.ANSWERING_QUESTION: {
            "base": 10,
            "min_multiplier": 1.0,
            "max_multiplier": 3.0,
        },
        ContributionType.CREATING_CONTENT: {
            "base": 25,
            "min_multiplier": 1.0,
            "max_multiplier": 5.0,
        },
        ContributionType.MODERATING: {
            "base": 50,
            "min_multiplier": 1.0,
            "max_multiplier": 2.0,
        },
        ContributionType.REPORTING_ISSUE: {
            "base": 5,
            "min_multiplier": 1.0,
            "max_multiplier": 2.0,
        },
        ContributionType.CODE_CONTRIBUTION: {
            "base": 100,
            "min_multiplier": 1.0,
            "max_multiplier": 10.0,
        },
        ContributionType.EVENT_PARTICIPATION: {
            "base": 15,
            "min_multiplier": 1.0,
            "max_multiplier": 1.5,
        },
        ContributionType.DAILY_ENGAGEMENT: {
            "base": 5,
            "min_multiplier": 1.0,
            "max_multiplier": 1.0,
        },
        ContributionType.HELPING_NEWCOMER: {
            "base": 20,
            "min_multiplier": 1.0,
            "max_multiplier": 4.0,
        },
        ContributionType.FEEDBACK_GIVING: {
            "base": 15,
            "min_multiplier": 1.0,
            "max_multiplier": 3.0,
        },
        ContributionType.TUTORIAL_CREATING: {
            "base": 75,
            "min_multiplier": 1.0,
            "max_multiplier": 5.0,
        },
        ContributionType.BUG_FIXING: {
            "base": 150,
            "min_multiplier": 1.0,
            "max_multiplier": 8.0,
        },
        ContributionType.COMMUNITY_SUPPORT: {
            "base": 30,
            "min_multiplier": 1.0,
            "max_multiplier": 3.0,
        },
    }
    
    # Keyword patterns for classification
    PATTERNS = {
        ContributionType.ANSWERING_QUESTION: [
            r"here('s| is) (how|what|why)",
            r"you (can|should|need to)",
            r"try (using|doing|this)",
            r"the (answer|solution) is",
            r"let me (help|explain|show)",
            r"based on.*experience",
            r"i('ve| have) (done|tried|used) this",
        ],
        ContributionType.HELPING_NEWCOMER: [
            r"welcome to",
            r"(new|first) (here|time)",
            r"check out.*guide",
            r"start (with|by)",
            r"don't worry",
            r"everyone starts somewhere",
        ],
        ContributionType.CODE_CONTRIBUTION: [
            r"```(python|javascript|typescript|rust)",
            r"pull request",
            r"(fixed|implemented|added) (the )?(bug|feature)",
            r"here('s| is) (the )?code",
            r"github\.com/.*/(pull|commit)",
        ],
        ContributionType.REPORTING_ISSUE: [
            r"(found|discovered) (a )?(bug|issue|problem)",
            r"(not|doesn't) (work|working)",
            r"error.*when",
            r"(having|getting) (an )?error",
        ],
        ContributionType.TUTORIAL_CREATING: [
            r"(tutorial|guide|walkthrough)",
            r"step (1|2|3|one|two|three)",
            r"how to.*:",
            r"first.*then.*finally",
        ],
        ContributionType.FEEDBACK_GIVING: [
            r"(suggest|recommend|propose)",
            r"(could|might|would) be (better|nice|good)",
            r"what if we",
            r"constructive (feedback|criticism)",
        ],
    }
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize classifier.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def classify_message(
        self,
        message: discord.Message,
        context: Optional[Dict[str, any]] = None,
    ) -> Optional[ContributionScore]:
        """
        Classify a Discord message and calculate reward.
        
        Args:
            message: Discord message to analyze
            context: Additional context (replied to, thread, etc.)
            
        Returns:
            ContributionScore or None if not a valuable contribution
        """
        # Check if message qualifies for classification
        if not await self._is_valid_contribution(message):
            return None
        
        # Detect contribution type
        contribution_type = await self._detect_contribution_type(message, context)
        if not contribution_type:
            return None
        
        # Calculate quality multiplier
        quality_multiplier = await self._calculate_quality(
            message,
            contribution_type,
            context,
        )
        
        # Get reward configuration
        config = self.REWARD_CONFIG[contribution_type]
        base_reward = config["base"]
        
        # Clamp multiplier
        quality_multiplier = max(
            config["min_multiplier"],
            min(quality_multiplier, config["max_multiplier"]),
        )
        
        # Calculate final reward
        final_reward = int(base_reward * quality_multiplier)
        
        # Generate reasoning
        reasoning = await self._generate_reasoning(
            message,
            contribution_type,
            quality_multiplier,
        )
        
        # Collect metadata
        metadata = {
            "message_id": message.id,
            "author_id": message.author.id,
            "channel_id": message.channel.id,
            "timestamp": message.created_at.isoformat(),
            "length": len(message.content),
            "has_code": "```" in message.content,
            "has_links": "http" in message.content.lower(),
            "reaction_count": sum(r.count for r in message.reactions),
        }
        
        return ContributionScore(
            contribution_type=contribution_type,
            base_reward=base_reward,
            quality_multiplier=quality_multiplier,
            final_reward=final_reward,
            confidence=0.85,  # Placeholder - would use ML model
            reasoning=reasoning,
            metadata=metadata,
        )
    
    async def _is_valid_contribution(self, message: discord.Message) -> bool:
        """Check if message is eligible for rewards."""
        # Ignore bots
        if message.author.bot:
            return False
        
        # Ignore very short messages
        if len(message.content.strip()) < 10:
            return False
        
        # Ignore spam patterns
        if await self._is_spam(message):
            return False
        
        return True
    
    async def _is_spam(self, message: discord.Message) -> bool:
        """Detect spam patterns."""
        content = message.content.lower()
        
        # Check for excessive repetition
        words = content.split()
        if len(words) > 3 and len(set(words)) / len(words) < 0.3:
            return True
        
        # Check for excessive caps
        if sum(1 for c in content if c.isupper()) / max(len(content), 1) > 0.7:
            return True
        
        # Check for excessive special characters
        special_chars = sum(1 for c in content if not c.isalnum() and not c.isspace())
        if special_chars / max(len(content), 1) > 0.5:
            return True
        
        return False
    
    async def _detect_contribution_type(
        self,
        message: discord.Message,
        context: Optional[Dict[str, any]],
    ) -> Optional[ContributionType]:
        """Detect the type of contribution."""
        import re
        
        content = message.content.lower()
        
        # Check each pattern
        scores = {}
        for contrib_type, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[contrib_type] = score
        
        # Return highest scoring type
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # Default classifications
        if context and context.get("is_reply"):
            return ContributionType.ANSWERING_QUESTION
        
        if len(message.content) > 500:
            return ContributionType.CREATING_CONTENT
        
        return ContributionType.DAILY_ENGAGEMENT
    
    async def _calculate_quality(
        self,
        message: discord.Message,
        contribution_type: ContributionType,
        context: Optional[Dict[str, any]],
    ) -> float:
        """
        Calculate quality multiplier based on various factors.
        
        Returns:
            float: Quality multiplier (1.0 = base quality)
        """
        multiplier = 1.0
        
        # Length bonus (up to +0.5)
        length = len(message.content)
        if length > 100:
            multiplier += min(0.5, (length - 100) / 1000)
        
        # Code block bonus (+0.5 for formatted code)
        if "```" in message.content:
            multiplier += 0.5
        
        # Reaction bonus (community validation)
        reaction_count = sum(r.count for r in message.reactions)
        if reaction_count > 0:
            multiplier += min(1.0, reaction_count * 0.1)
        
        # Link/resource bonus (+0.3 for helpful links)
        if "http" in message.content.lower():
            multiplier += 0.3
        
        # Thread context bonus
        if context and context.get("in_thread"):
            multiplier += 0.2
        
        # Newbie helper bonus
        if context and context.get("helping_new_user"):
            multiplier += 0.5
        
        # Detailed explanation bonus (for longer, structured answers)
        if contribution_type == ContributionType.ANSWERING_QUESTION:
            if length > 200 and ("1." in message.content or "•" in message.content):
                multiplier += 0.4
        
        return multiplier
    
    async def _generate_reasoning(
        self,
        message: discord.Message,
        contribution_type: ContributionType,
        quality_multiplier: float,
    ) -> str:
        """Generate human-readable reasoning for the reward."""
        base_reasons = {
            ContributionType.ANSWERING_QUESTION: "Helped answer a community question",
            ContributionType.CREATING_CONTENT: "Created valuable content for the community",
            ContributionType.MODERATING: "Helped moderate community discussions",
            ContributionType.HELPING_NEWCOMER: "Welcomed and assisted a new member",
            ContributionType.CODE_CONTRIBUTION: "Contributed code to the project",
        }
        
        base = base_reasons.get(
            contribution_type,
            f"Made a {contribution_type.value.replace('_', ' ')} contribution",
        )
        
        # Add quality factors
        factors = []
        if len(message.content) > 200:
            factors.append("detailed explanation")
        if "```" in message.content:
            factors.append("included code examples")
        if sum(r.count for r in message.reactions) > 2:
            factors.append("well-received by community")
        
        if factors:
            return f"{base} with {', '.join(factors)}"
        else:
            return base
    
    async def classify_bulk_messages(
        self,
        messages: List[discord.Message],
    ) -> Dict[int, ContributionScore]:
        """
        Classify multiple messages in bulk.
        
        Args:
            messages: List of messages to classify
            
        Returns:
            Dict mapping message IDs to scores
        """
        results = {}
        
        for message in messages:
            score = await self.classify_message(message)
            if score:
                results[message.id] = score
        
        logger.info(
            "Bulk classification complete",
            total_messages=len(messages),
            classified=len(results),
        )
        
        return results
    
    async def get_contribution_stats(
        self,
        user_id: int,
        days: int = 30,
    ) -> Dict[str, any]:
        """
        Get contribution statistics for a user.
        
        Args:
            user_id: Discord user ID
            days: Number of days to analyze
            
        Returns:
            Dictionary of statistics
        """
        # This would query the database for actual stats
        # Placeholder implementation
        return {
            "total_contributions": 42,
            "total_tokens_earned": 1337,
            "top_contribution_type": ContributionType.ANSWERING_QUESTION,
            "average_quality": 1.8,
            "streak_days": 7,
            "rank": "Top 10%",
        }
