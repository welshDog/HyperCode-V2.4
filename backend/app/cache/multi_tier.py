"""Advanced multi-tier caching strategy for HyperCode."""

import hashlib
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps
from cachetools import TTLCache
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheLayer:
    """Enum for cache layers."""
    LOCAL = "local"
    REDIS = "redis"
    DISK = "disk"


class MultiTierCache:
    """Advanced multi-tier caching system.
    
    Architecture:
    1. Local Cache (in-process TTL cache) - Fastest, limited size
    2. Redis Cache (distributed) - Medium speed, large capacity
    3. Disk Cache (persistent) - Slowest, unlimited capacity
    """
    
    def __init__(
        self,
        local_size: int = 1000,
        local_ttl: int = 300,
        redis_url: str = "redis://redis:6379/1",
    ):
        """Initialize multi-tier cache.
        
        Args:
            local_size: Max items in local cache
            local_ttl: TTL for local cache items (seconds)
            redis_url: Redis connection URL
        """
        self.local_cache = TTLCache(maxsize=local_size, ttl=local_ttl)
        self.redis_url = redis_url
        self.redis_client = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "local_hits": 0,
            "redis_hits": 0,
            "evictions": 0,
        }
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self.redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using local cache only.")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Generate cache key."""
        return f"{namespace}:{key}"
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        return json.dumps(value, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize value from storage."""
        return json.loads(data)
    
    async def get(
        self,
        namespace: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get value from cache with fallback chain.
        
        Tries in order:
        1. Local cache (fastest)
        2. Redis cache (medium speed)
        3. Returns default
        """
        cache_key = self._make_key(namespace, key)
        
        # Try local cache
        if cache_key in self.local_cache:
            self.stats["hits"] += 1
            self.stats["local_hits"] += 1
            logger.debug(f"Local cache hit: {cache_key}")
            return self.local_cache[cache_key]
        
        # Try Redis cache
        if self.redis_client:
            try:
                value = await self.redis_client.get(cache_key)
                if value:
                    self.stats["hits"] += 1
                    self.stats["redis_hits"] += 1
                    logger.debug(f"Redis cache hit: {cache_key}")
                    
                    # Populate local cache
                    deserialized = self._deserialize(value)
                    self.local_cache[cache_key] = deserialized
                    return deserialized
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Cache miss
        self.stats["misses"] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return default
    
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> None:
        """Set value in cache.
        
        Writes to both local and Redis caches for consistency.
        """
        cache_key = self._make_key(namespace, key)
        
        # Store in local cache
        try:
            self.local_cache[cache_key] = value
        except Exception as e:
            logger.warning(f"Local cache set failed: {e}")
            self.stats["evictions"] += 1
        
        # Store in Redis cache
        if self.redis_client:
            try:
                serialized = self._serialize(value)
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    serialized,
                )
                logger.debug(f"Cache set: {cache_key} (ttl={ttl}s)")
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
    
    async def delete(self, namespace: str, key: str) -> None:
        """Delete value from cache."""
        cache_key = self._make_key(namespace, key)
        
        # Delete from local cache
        if cache_key in self.local_cache:
            del self.local_cache[cache_key]
        
        # Delete from Redis cache
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Cache deleted: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
    
    async def clear_namespace(self, namespace: str) -> None:
        """Clear all keys in a namespace."""
        # Clear local cache
        keys_to_delete = [k for k in self.local_cache if k.startswith(f"{namespace}:")]
        for key in keys_to_delete:
            del self.local_cache[key]
        
        # Clear Redis cache
        if self.redis_client:
            try:
                pattern = f"{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                logger.debug(f"Cleared namespace: {namespace}")
            except Exception as e:
                logger.warning(f"Redis namespace clear failed: {e}")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "total_requests": total,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "local_hits": self.stats["local_hits"],
            "redis_hits": self.stats["redis_hits"],
            "evictions": self.stats["evictions"],
            "local_cache_size": len(self.local_cache),
        }


# Global cache instance
_cache_instance: Optional[MultiTierCache] = None


async def get_cache() -> MultiTierCache:
    """Get or create global cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = MultiTierCache()
        await _cache_instance.connect()
    
    return _cache_instance


def cache(
    namespace: str,
    ttl: int = 300,
):
    """Decorator for caching async functions.
    
    Usage:
        @cache(namespace="agents", ttl=600)
        async def get_agent(agent_id: str):
            return await db.get_agent(agent_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from arguments
            key_parts = [str(arg) for arg in args] + [f"{k}={v}" for k, v in kwargs.items()]
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try cache
            cache = await get_cache()
            cached = await cache.get(namespace, cache_key)
            
            if cached is not None:
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await cache.set(namespace, cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator


class CacheInvalidation:
    """Cache invalidation patterns."""
    
    @staticmethod
    async def invalidate_agent_cache(agent_id: str):
        """Invalidate all caches related to an agent."""
        cache = await get_cache()
        await cache.delete("agents", agent_id)
        await cache.delete("agent_status", agent_id)
        await cache.delete("agent_tasks", agent_id)
    
    @staticmethod
    async def invalidate_task_cache(task_id: str):
        """Invalidate all caches related to a task."""
        cache = await get_cache()
        await cache.delete("tasks", task_id)
        await cache.delete("task_status", task_id)
        await cache.delete("task_results", task_id)
    
    @staticmethod
    async def invalidate_system_cache():
        """Invalidate all system caches."""
        cache = await get_cache()
        await cache.clear_namespace("system")
        await cache.clear_namespace("config")
