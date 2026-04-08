import asyncio
import uuid
import json
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
import redis.asyncio as redis

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"

class ApprovalSystem:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis = None
    
    async def connect(self):
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)

    async def request_approval(
        self,
        agent_name: str,
        action_type: str,
        action_details: Dict[str, Any],
        timeout: int = 300  # 5 minutes default
    ) -> Dict[str, Any]:
        """Agent requests human approval before executing action"""
        await self.connect()
        
        approval_id = str(uuid.uuid4())
        
        # Store approval request
        approval_request = {
            "id": approval_id,
            "agent": agent_name,
            "action_type": action_type,
            "details": action_details,
            "status": ApprovalStatus.PENDING.value,
            "created_at": datetime.now().isoformat()
        }
        
        await self.redis.set(
            f"approval:{approval_id}",
            json.dumps(approval_request),
            ex=timeout
        )
        
        # Publish to approval channel (Dashboard listens here)
        await self.redis.publish(
            "approval_requests",
            json.dumps(approval_request)
        )
        
        # Wait for human response (blocking with timeout)
        result = await self._wait_for_response(approval_id, timeout)
        
        return result
    
    async def _wait_for_response(self, approval_id: str, timeout: int) -> Dict[str, Any]:
        """Wait for human to approve/reject via Dashboard"""
        
        # Poll for response (could also use pub/sub)
        start_time = datetime.now().timestamp()
        while (datetime.now().timestamp() - start_time) < timeout:
            response = await self.redis.get(f"approval:{approval_id}:response")
            
            if response:
                return json.loads(response)
            
            await asyncio.sleep(1)
        
        # Timeout - default to rejection for safety
        return {
            "status": ApprovalStatus.REJECTED.value,
            "reason": "Timeout - no human response received"
        }
    
    async def respond_to_approval(
        self,
        approval_id: str,
        status: str, # "approved", "rejected", "modified"
        modifications: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None
    ):
        """Human responds via Dashboard"""
        await self.connect()
        
        response = {
            "status": status,
            "modifications": modifications,
            "reason": reason,
            "responded_at": datetime.now().isoformat()
        }
        
        # Update the original request status too
        request_json = await self.redis.get(f"approval:{approval_id}")
        if request_json:
            request = json.loads(request_json)
            request["status"] = status
            await self.redis.set(f"approval:{approval_id}", json.dumps(request))

        await self.redis.set(
            f"approval:{approval_id}:response",
            json.dumps(response),
            ex=3600
        )
