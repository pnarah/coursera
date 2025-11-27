from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings
from typing import Optional

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def init_redis_pool():
    """Initialize Redis connection pool."""
    global _redis_pool, _redis_client
    
    _redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10,
    )
    _redis_client = Redis(connection_pool=_redis_pool)
    
    # Test connection
    await _redis_client.ping()
    print("✓ Redis connection established")


async def close_redis_pool():
    """Close Redis connection pool."""
    global _redis_pool, _redis_client
    
    if _redis_client:
        await _redis_client.close()
    if _redis_pool:
        await _redis_pool.disconnect()
    print("✓ Redis connection closed")


async def get_redis() -> Redis:
    """Dependency for getting Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client
