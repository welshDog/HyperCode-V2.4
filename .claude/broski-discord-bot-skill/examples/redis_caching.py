"""
Redis Caching Pattern for Discord Bots
Sub-2ms data access with automatic cache invalidation
"""

import os
import redis.asyncio as redis
import json
import asyncpg
from typing import Optional, Dict, Any


class BotCache:
    """Redis cache manager with PostgreSQL fallback"""
    
    def __init__(self, redis_url: str, db_pool: asyncpg.Pool):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.db_pool = db_pool
    
    async def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get guild config with caching. ~2ms hit, ~10ms miss."""
        cache_key = f"guild:{guild_id}:config"
        
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild_id)
        
        config = dict(row) if row else {"guild_id": guild_id, "prefix": "!", "moderation_enabled": True}
        await self.redis.setex(cache_key, 3600, json.dumps(config))
        return config
    
    async def update_guild_config(self, guild_id: int, updates: Dict[str, Any]) -> None:
        """Update config and invalidate cache."""
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(updates.keys())])
        values = [guild_id] + list(updates.values())
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(f"UPDATE guilds SET {set_clause} WHERE guild_id = $1", *values)
        
        await self.redis.delete(f"guild:{guild_id}:config")
    
    async def check_rate_limit(self, user_id: int, command: str, limit: int = 5, window: int = 60) -> bool:
        """Returns True if allowed, False if rate limited."""
        key = f"ratelimit:{user_id}:{command}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, window)
        return count <= limit
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache hit/miss statistics."""
        info = await self.redis.info('stats')
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 1)
        return {"hits": hits, "misses": misses, "hit_rate": (hits / (hits + misses)) * 100}
