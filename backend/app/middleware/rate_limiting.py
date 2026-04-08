"""Rate limiting and security middleware for HyperCode API."""

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
import time
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Global default
    storage_uri="redis://redis:6379/2"  # Use Redis for persistence
)


class RateLimitConfig:
    """Configuration for rate limiting per endpoint."""
    
    # Endpoint-specific limits (requests per minute)
    LIMITS = {
        # Public endpoints
        "/health": "1000/minute",
        "/docs": "100/minute",
        "/openapi.json": "100/minute",
        
        # Authentication
        "/api/auth/login": "5/minute",  # Prevent brute force
        "/api/auth/register": "3/minute",
        "/api/auth/logout": "100/minute",
        "/api/auth/refresh": "30/minute",
        
        # API endpoints
        "/api/agents": "100/minute",
        "/api/agents/{agent_id}": "100/minute",
        "/api/tasks": "50/minute",
        "/api/tasks/{task_id}": "100/minute",
        "/api/tasks/*/submit": "30/minute",
        
        # WebSocket (excluded from rate limiting in decorator)
        "/ws": "unlimited",
    }
    
    # Custom rate limit per authenticated user
    AUTHENTICATED_LIMITS = {
        "default": "500/minute",  # Increase for authenticated users
        "admin": "unlimited",
        "premium": "1000/minute",
    }


def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Custom error handler for rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": 60,
            "limit": exc.detail
        }
    )


def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting for FastAPI application."""
    
    # Add rate limiter to app state
    app.state.limiter = limiter
    
    # Add exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    
    logger.info("Rate limiting configured")


def get_rate_limit_key(request: Request, user_role: str = None) -> str:
    """Get rate limit key based on user/IP."""
    if user_role and user_role in RateLimitConfig.AUTHENTICATED_LIMITS:
        return f"user:{user_role}"
    
    return get_remote_address(request)


# Decorator for protected endpoints
def rate_limit(limit: str = None):
    """Decorator for applying rate limits to endpoints."""
    def decorator(func):
        if limit:
            return limiter.limit(limit)(func)
        return func
    return decorator


# Example: Async rate limiter for high-throughput endpoints
class AsyncRateLimiter:
    """Async-safe rate limiter for background tasks."""
    
    def __init__(self, redis_url: str = "redis://redis:6379/3"):
        self.redis_url = redis_url
        self.redis = None
    
    async def connect(self):
        """Connect to Redis."""
        import redis.asyncio as aio_redis
        self.redis = await aio_redis.from_url(self.redis_url)
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit.
        
        Args:
            key: Rate limit key (IP, user ID, etc)
            limit: Max requests allowed
            window: Time window in seconds
        
        Returns:
            True if allowed, False if rate limited
        """
        if not self.redis:
            await self.connect()
        
        current_time = int(time.time())
        window_key = f"rate_limit:{key}:{current_time // window}"
        
        # Increment counter
        count = await self.redis.incr(window_key)
        
        # Set expiry on first increment
        if count == 1:
            await self.redis.expire(window_key, window)
        
        return count <= limit
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()


# Global async rate limiter instance
async_limiter = None


async def get_async_limiter():
    """Get or create async rate limiter."""
    global async_limiter
    if async_limiter is None:
        async_limiter = AsyncRateLimiter()
        await async_limiter.connect()
    return async_limiter
