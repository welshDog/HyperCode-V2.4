import redis
import json
from datetime import datetime
from typing import Dict, List, Any

class ProjectMemory:
    """Shared memory across all agents - like a hive mind"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.project_key = "hypercode:project_state"
    
    def update_tech_stack(self, component: str, technology: str, added_by: str):
        """Record technology decisions"""
        self.redis.hset(
            f"{self.project_key}:tech_stack",
            component,
            json.dumps({
                "technology": technology,
                "added_at": datetime.now().isoformat(),
                "added_by": added_by
            })
        )
    
    def add_api_endpoint(self, endpoint: Dict[str, Any]):
        """Backend agent records new API"""
        self.redis.lpush(
            f"{self.project_key}:api_endpoints",
            json.dumps(endpoint)
        )
    
    def get_available_apis(self) -> List[Dict[str, Any]]:
        """Frontend agent queries available APIs"""
        endpoints = self.redis.lrange(
            f"{self.project_key}:api_endpoints",
            0, -1
        )
        return [json.loads(e) for e in endpoints] if endpoints else []
    
    def record_decision(self, decision: Dict[str, Any]):
        """Track architectural decisions"""
        self.redis.lpush(
            f"{self.project_key}:decisions",
            json.dumps({
                **decision,
                "timestamp": datetime.now().isoformat()
            })
        )
    
    def get_project_context(self) -> Dict[str, Any]:
        """Get complete project state for agent context"""
        tech_stack = self.redis.hgetall(f"{self.project_key}:tech_stack")
        return {
            "tech_stack": {k: json.loads(v) for k, v in tech_stack.items()},
            "api_endpoints": self.get_available_apis(),
            "recent_decisions": [json.loads(d) for d in self.redis.lrange(f"{self.project_key}:decisions", 0, 9)],
            "active_features": list(self.redis.smembers(f"{self.project_key}:features")),
            "known_issues": [json.loads(i) for i in self.redis.lrange(f"{self.project_key}:issues", 0, 9)]
        }
