"""
Shared utilities for all agents: caching, rate limiting, circuit breaker, metrics
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional
from enum import Enum

import redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest

# ============================================================================
# REDIS CACHING
# ============================================================================

class RedisCache:
    """Singleton Redis connection for all agents."""
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def client(self):
        if self._redis is None:
            self._redis = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5
            )
            try:
                self._redis.ping()
            except Exception as e:
                print(f"Redis connection failed: {e}. Caching disabled.")
                self._redis = None
        return self._redis

    def get(self, key: str) -> Optional[str]:
        try:
            if self.client:
                return self.client.get(key)
        except Exception as e:
            print(f"Redis GET failed: {e}")
        return None

    def set(self, key: str, value: str, ttl: int = 3600):
        try:
            if self.client:
                self.client.setex(key, ttl, value)
        except Exception as e:
            print(f"Redis SET failed: {e}")


def cached(ttl_seconds: int = 3600):
    """Decorator for caching function results in Redis."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = RedisCache()
            cache_key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            import json
            try:
                cache.set(cache_key, json.dumps(result), ttl_seconds)
            except:
                cache.set(cache_key, str(result), ttl_seconds)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = RedisCache()
            cache_key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            
            import json
            try:
                cache.set(cache_key, json.dumps(result), ttl_seconds)
            except:
                cache.set(cache_key, str(result), ttl_seconds)
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# RATE LIMITING
# ============================================================================

limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitState(Enum):
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject immediately
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreaker:
    """Circuit breaker for resilient agent-to-agent calls."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._state = CircuitState.CLOSED
        
        self._metrics = {
            "state_changes": Counter(
                f"{name}_circuit_state_changes",
                f"State changes for {name}",
                ["from_state", "to_state"]
            ),
            "calls": Counter(
                f"{name}_circuit_calls",
                f"Total calls through {name} circuit",
                ["state", "result"]
            ),
        }
    
    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
        return self._state
    
    def _transition(self, new_state: CircuitState):
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            print(f"[{self.name}] Circuit breaker: {old_state.value} → {new_state.value}")
            self._metrics["state_changes"].labels(
                from_state=old_state.value,
                to_state=new_state.value
            ).inc()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute func through circuit breaker."""
        if self.state == CircuitState.OPEN:
            self._metrics["calls"].labels(
                state=self._state.value,
                result="rejected"
            ).inc()
            raise Exception(f"Circuit breaker OPEN for {self.name}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async func through circuit breaker."""
        if self.state == CircuitState.OPEN:
            self._metrics["calls"].labels(
                state=self._state.value,
                result="rejected"
            ).inc()
            raise Exception(f"Circuit breaker OPEN for {self.name}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        self.failure_count = 0
        self.success_count += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.CLOSED)
        
        self._metrics["calls"].labels(
            state=self._state.value,
            result="success"
        ).inc()
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN)
        
        self._metrics["calls"].labels(
            state=self._state.value,
            result="failure"
        ).inc()


# ============================================================================
# PROMETHEUS METRICS REGISTRY (Shared)
# ============================================================================

class AgentMetrics:
    """Centralized metrics for all agents."""
    
    _registry = CollectorRegistry()
    
    @classmethod
    def get_registry(cls):
        return cls._registry
    
    @classmethod
    def create_counter(cls, name: str, description: str, labels=None):
        return Counter(name, description, labels or [], registry=cls._registry)
    
    @classmethod
    def create_histogram(cls, name: str, description: str, labels=None, buckets=None):
        return Histogram(
            name,
            description,
            labels or [],
            registry=cls._registry,
            buckets=buckets or (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
    
    @classmethod
    def generate_latest(cls):
        return generate_latest(cls._registry)
