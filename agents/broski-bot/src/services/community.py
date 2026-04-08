"""
Community management and token distribution services.
Handles contribution tracking, reward calculations, and token operations.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.contribution_classifier import (
    AIContributionClassifier,
    ContributionScore,
)
from src.config.logging import LoggerMixin, get_logger
from src.core.exceptions import InsufficientBalanceException
from src.models import Contribution, TokenTransaction
from src.repositories import EconomyRepository

logger = get_logger(__name__)


class CommunityService(LoggerMixin):
    """
    Service for managing community contributions and engagement.
    
    Tracks all community interactions, calculates reputation scores,
    and coordinates with token distribution.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize community service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.classifier = AIContributionClassifier(session)
        self.economy_repo = EconomyRepository(session)
    
    async def process_contribution(
        self,
        user_id: int,
        message_id: int,
        channel_id: int,
        guild_id: int,
        score: ContributionScore,
    ) -> Contribution:
        """
        Process and record a community contribution.
        
        Args:
            user_id: Discord user ID
            message_id: Message ID
            channel_id: Channel ID
            guild_id: Guild ID
            score: Contribution score from classifier
            
        Returns:
            Created contribution record
        """
        # Create contribution record
        contribution = Contribution(
            user_id=user_id,
            message_id=message_id,
            channel_id=channel_id,
            guild_id=guild_id,
            contribution_type=score.contribution_type,
            base_reward=score.base_reward,
            quality_multiplier=score.quality_multiplier,
            final_reward=score.final_reward,
            confidence=score.confidence,
            reasoning=score.reasoning,
            metadata=score.metadata,
        )
        
        self.session.add(contribution)
        
        # Award tokens
        await self.economy_repo.add_balance(user_id, score.final_reward)
        
        # Create token transaction record
        transaction = TokenTransaction(
            user_id=user_id,
            amount=score.final_reward,
            transaction_type="contribution_reward",
            source="ai_classifier",
            reference_id=message_id,
            metadata={
                "contribution_type": score.contribution_type.value,
                "quality": score.quality_multiplier,
            },
        )
        
        self.session.add(transaction)
        await self.session.commit()
        
        self.logger.info(
            "Contribution processed",
            user_id=user_id,
            contribution_type=score.contribution_type.value,
            reward=score.final_reward,
        )
        
        return contribution
    
    async def get_user_reputation(self, user_id: int) -> Dict[str, any]:
        """
        Calculate user reputation based on contributions.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary of reputation metrics
        """
        # Get contribution statistics
        stmt = (
            select(
                func.count(Contribution.id).label("total_contributions"),
                func.sum(Contribution.final_reward).label("total_earned"),
                func.avg(Contribution.quality_multiplier).label("avg_quality"),
                func.max(Contribution.created_at).label("last_contribution"),
            )
            .where(Contribution.user_id == user_id)
        )
        
        result = await self.session.execute(stmt)
        stats = result.one()
        
        # Calculate reputation score (0-100)
        reputation_score = await self._calculate_reputation_score(user_id, stats)
        
        # Get contribution type breakdown
        type_breakdown = await self._get_contribution_breakdown(user_id)
        
        # Calculate rank
        rank = await self._get_user_rank(user_id)
        
        return {
            "reputation_score": reputation_score,
            "total_contributions": stats.total_contributions or 0,
            "total_earned": int(stats.total_earned or 0),
            "average_quality": float(stats.avg_quality or 0),
            "last_contribution": stats.last_contribution,
            "contribution_breakdown": type_breakdown,
            "rank": rank,
            "tier": await self._get_reputation_tier(reputation_score),
        }
    
    async def _calculate_reputation_score(
        self,
        user_id: int,
        stats: any,
    ) -> int:
        """Calculate 0-100 reputation score."""
        score = 0
        
        # Contribution count (max 30 points)
        contribution_count = stats.total_contributions or 0
        score += min(30, contribution_count)
        
        # Quality average (max 30 points)
        avg_quality = stats.avg_quality or 0
        score += min(30, int(avg_quality * 10))
        
        # Total earned (max 20 points)
        total_earned = stats.total_earned or 0
        score += min(20, int(total_earned / 100))
        
        # Recency bonus (max 20 points)
        if stats.last_contribution:
            days_ago = (datetime.utcnow() - stats.last_contribution).days
            recency_score = max(0, 20 - days_ago)
            score += recency_score
        
        return min(100, score)
    
    async def _get_contribution_breakdown(
        self,
        user_id: int,
    ) -> Dict[str, int]:
        """Get count of each contribution type."""
        stmt = (
            select(
                Contribution.contribution_type,
                func.count(Contribution.id).label("count"),
            )
            .where(Contribution.user_id == user_id)
            .group_by(Contribution.contribution_type)
        )
        
        result = await self.session.execute(stmt)
        return {row.contribution_type: row.count for row in result}
    
    async def _get_user_rank(self, user_id: int) -> str:
        """Get user's ranking among all contributors."""
        # This would query all users and rank them
        # Simplified implementation
        return "Top 10%"
    
    async def _get_reputation_tier(self, score: int) -> str:
        """Get reputation tier based on score."""
        if score >= 90:
            return "🏆 Legendary BROski"
        elif score >= 75:
            return "💎 Diamond BROski"
        elif score >= 60:
            return "⭐ Gold BROski"
        elif score >= 40:
            return "🥈 Silver BROski"
        elif score >= 20:
            return "🥉 Bronze BROski"
        else:
            return "🆕 New BROski"
    
    async def get_leaderboard(
        self,
        metric: str = "total_earned",
        limit: int = 10,
    ) -> List[Dict[str, any]]:
        """
        Get community leaderboard.
        
        Args:
            metric: Metric to rank by (total_earned, contributions, quality)
            limit: Number of results
            
        Returns:
            List of top contributors
        """
        if metric == "total_earned":
            order_col = func.sum(Contribution.final_reward).desc()
        elif metric == "contributions":
            order_col = func.count(Contribution.id).desc()
        else:
            order_col = func.avg(Contribution.quality_multiplier).desc()
        
        stmt = (
            select(
                Contribution.user_id,
                func.count(Contribution.id).label("total_contributions"),
                func.sum(Contribution.final_reward).label("total_earned"),
                func.avg(Contribution.quality_multiplier).label("avg_quality"),
            )
            .group_by(Contribution.user_id)
            .order_by(order_col)
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        
        leaderboard = []
        for row in result:
            leaderboard.append({
                "user_id": row.user_id,
                "total_contributions": row.total_contributions,
                "total_earned": int(row.total_earned or 0),
                "average_quality": float(row.avg_quality or 0),
            })
        
        return leaderboard


class TokenDistributionService(LoggerMixin):
    """
    Service for managing token distribution and conversions.
    
    Handles internal BROski$ ledger, conversions to MintMe blockchain,
    and distribution algorithms.
    """
    
    # Conversion rate: 1000 internal BROski$ = 1 MintMe BROski token
    CONVERSION_RATE = 1000
    MIN_CONVERSION_AMOUNT = 1000
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize token distribution service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.economy_repo = EconomyRepository(session)
    
    async def distribute_tokens(
        self,
        user_id: int,
        amount: int,
        reason: str,
        metadata: Optional[Dict] = None,
    ) -> TokenTransaction:
        """
        Distribute tokens to a user.
        
        Args:
            user_id: Recipient user ID
            amount: Amount of tokens
            reason: Reason for distribution
            metadata: Additional data
            
        Returns:
            Token transaction record
        """
        # Add to user balance
        await self.economy_repo.add_balance(user_id, amount)
        
        # Create transaction record
        transaction = TokenTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type="distribution",
            source=reason,
            metadata=metadata or {},
        )
        
        self.session.add(transaction)
        await self.session.commit()
        
        self.logger.info(
            "Tokens distributed",
            user_id=user_id,
            amount=amount,
            reason=reason,
        )
        
        return transaction
    
    async def convert_to_mintme(
        self,
        user_id: int,
        amount: int,
    ) -> Tuple[TokenTransaction, str]:
        """
        Convert internal tokens to MintMe blockchain tokens.
        
        Args:
            user_id: User ID
            amount: Amount to convert (must be >= MIN_CONVERSION_AMOUNT)
            
        Returns:
            Tuple of (transaction, blockchain_tx_hash)
            
        Raises:
            InsufficientBalanceException: If user doesn't have enough tokens
            ValueError: If amount is below minimum
        """
        if amount < self.MIN_CONVERSION_AMOUNT:
            raise ValueError(
                f"Minimum conversion amount is {self.MIN_CONVERSION_AMOUNT} BROski$"
            )
        
        # Check user balance
        economy = await self.economy_repo.get_or_create(user_id)
        if economy.balance < amount:
            raise InsufficientBalanceException(amount, economy.balance)
        
        # Calculate MintMe tokens
        mintme_tokens = amount / self.CONVERSION_RATE
        
        # Deduct internal balance
        await self.economy_repo.subtract_balance(user_id, amount)
        
        # TODO: Actual MintMe blockchain transaction
        # For now, simulate with placeholder hash
        blockchain_tx = f"0x{user_id:016x}{int(datetime.utcnow().timestamp()):08x}"
        
        # Create transaction record
        transaction = TokenTransaction(
            user_id=user_id,
            amount=-amount,  # Negative for conversion
            transaction_type="conversion_to_mintme",
            source="mintme_bridge",
            reference_id=blockchain_tx,
            metadata={
                "mintme_tokens": mintme_tokens,
                "conversion_rate": self.CONVERSION_RATE,
            },
        )
        
        self.session.add(transaction)
        await self.session.commit()
        
        self.logger.info(
            "Tokens converted to MintMe",
            user_id=user_id,
            internal_amount=amount,
            mintme_tokens=mintme_tokens,
            tx_hash=blockchain_tx,
        )
        
        return transaction, blockchain_tx
    
    async def get_conversion_status(self, user_id: int) -> Dict[str, any]:
        """
        Get user's conversion eligibility and statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with conversion info
        """
        economy = await self.economy_repo.get_or_create(user_id)
        
        can_convert = economy.balance >= self.MIN_CONVERSION_AMOUNT
        mintme_tokens_available = economy.balance / self.CONVERSION_RATE
        
        # Get past conversions
        stmt = (
            select(func.count(TokenTransaction.id))
            .where(TokenTransaction.user_id == user_id)
            .where(TokenTransaction.transaction_type == "conversion_to_mintme")
        )
        result = await self.session.execute(stmt)
        conversion_count = result.scalar()
        
        return {
            "current_balance": economy.balance,
            "conversion_rate": self.CONVERSION_RATE,
            "min_conversion": self.MIN_CONVERSION_AMOUNT,
            "can_convert": can_convert,
            "mintme_tokens_available": mintme_tokens_available,
            "conversion_count": conversion_count,
            "next_milestone": self._calculate_next_milestone(economy.balance),
        }
    
    def _calculate_next_milestone(self, current_balance: int) -> Dict[str, any]:
        """Calculate next conversion milestone."""
        milestones = [1000, 5000, 10000, 25000, 50000, 100000]
        
        for milestone in milestones:
            if current_balance < milestone:
                return {
                    "amount": milestone,
                    "remaining": milestone - current_balance,
                    "progress_pct": (current_balance / milestone) * 100,
                }
        
        return {
            "amount": current_balance + 100000,
            "remaining": 100000,
            "progress_pct": 0,
        }
    
    async def get_token_flow_analytics(
        self,
        days: int = 30,
    ) -> Dict[str, any]:
        """
        Get token distribution analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics dictionary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total distributed
        stmt = (
            select(func.sum(TokenTransaction.amount))
            .where(TokenTransaction.created_at >= cutoff_date)
            .where(TokenTransaction.amount > 0)
        )
        result = await self.session.execute(stmt)
        total_distributed = result.scalar() or 0
        
        # Total converted
        stmt = (
            select(func.sum(TokenTransaction.amount))
            .where(TokenTransaction.created_at >= cutoff_date)
            .where(TokenTransaction.transaction_type == "conversion_to_mintme")
        )
        result = await self.session.execute(stmt)
        total_converted = abs(result.scalar() or 0)
        
        # Distribution by type
        stmt = (
            select(
                TokenTransaction.source,
                func.sum(TokenTransaction.amount).label("total"),
            )
            .where(TokenTransaction.created_at >= cutoff_date)
            .where(TokenTransaction.amount > 0)
            .group_by(TokenTransaction.source)
        )
        result = await self.session.execute(stmt)
        distribution_breakdown = {row.source: int(row.total) for row in result}
        
        return {
            "period_days": days,
            "total_distributed": int(total_distributed),
            "total_converted": int(total_converted),
            "conversion_rate_pct": (
                (total_converted / total_distributed * 100) if total_distributed > 0 else 0
            ),
            "distribution_breakdown": distribution_breakdown,
            "average_daily_distribution": int(total_distributed / days),
        }
