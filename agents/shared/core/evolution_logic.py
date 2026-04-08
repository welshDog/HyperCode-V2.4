"""
HyperCode Evolution Protocol Logic
Handles validation, deduplication, and persistence of improvement requests.
"""
import logging
import redis.asyncio as redis
from typing import Optional, Tuple
from agents.shared.protocols.evolution import ImprovementRequest, EvolutionStatus

logger = logging.getLogger("evolution.core")

class EvolutionProtocol:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.STREAM_KEY = "events:improvement_requested"
        self.DEDUP_PREFIX = "dedup:improvement:"
        self.TTL_SECONDS = 86400  # 24 hours

    async def submit_request(self, request: ImprovementRequest) -> Tuple[bool, str]:
        """
        Validates and submits an improvement request.
        Returns (success, message_or_error).
        """
        try:
            # 1. Validation (Pydantic handles schema validation automatically)
            req_hash = request.generate_hash()
            
            # 2. Idempotency Check
            is_duplicate = await self.redis.exists(f"{self.DEDUP_PREFIX}{req_hash}")
            if is_duplicate:
                logger.warning(f"Duplicate request detected: {request.id}")
                return False, "Duplicate request detected within 24h window"

            # 3. Persistence & Event Emission (Atomic Pipeline)
            async with self.redis.pipeline(transaction=True) as pipe:
                # Store deduplication key
                await pipe.set(f"{self.DEDUP_PREFIX}{req_hash}", request.id, ex=self.TTL_SECONDS)
                
                # Add to Stream (The Event)
                event_payload = request.model_dump_json()
                await pipe.xadd(self.STREAM_KEY, {"payload": event_payload})
                
                await pipe.execute()

            logger.info(f"Improvement Request submitted: {request.id}")
            return True, request.id

        except Exception as e:
            logger.error(f"Failed to submit request: {str(e)}", exc_info=True)
            return False, f"Internal error: {str(e)}"

    async def get_request_status(self, request_id: str) -> Optional[EvolutionStatus]:
        """Placeholder for status lookup logic (future implementation)"""
        # In a real implementation, we would query a persistent store or a status hash in Redis
        pass
