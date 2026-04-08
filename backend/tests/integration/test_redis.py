import pytest
import redis.asyncio as redis
import redis as sync_redis

def is_redis_available():
    """Check if Redis is available at localhost:6379."""
    try:
        # Use a short timeout to avoid hanging the test collection
        r = sync_redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        return r.ping()
    except Exception:
        return False

@pytest.mark.skipif(not is_redis_available(), reason="Redis is not available at localhost:6379")
@pytest.mark.asyncio
async def test_redis_operations():
    """
    Test basic Redis operations: connect, set, get, delete.
    """
    redis_host = 'localhost'
    redis_port = 6379
    
    # 1. Connect to Redis
    client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    
    try:
        # Verify connection
        assert await client.ping() is True
        
        key = "test_key"
        value = "test_value"
        
        # 2. Perform set operation
        await client.set(key, value)
        
        # 2. Perform get operation
        fetched_value = await client.get(key)
        assert fetched_value == value
        
        # 2. Perform delete operation
        await client.delete(key)
        
        # Verify deletion
        deleted_value = await client.get(key)
        assert deleted_value is None
        
    finally:
        # Close the connection
        await client.aclose()
