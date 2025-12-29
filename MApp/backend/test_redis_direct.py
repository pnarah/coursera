import asyncio
from redis.asyncio import Redis

async def test_redis():
    redis = Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    
    # Test connection
    pong = await redis.ping()
    print(f"Ping: {pong}")
    
    # Test set/get
    await redis.setex("test_key", 60, "test_value")
    value = await redis.get("test_key")
    print(f"Set and Get: {value}")
    
    # Test OTP key
    await redis.setex("otp:test123", 60, "654321")
    otp = await redis.get("otp:test123")
    print(f"OTP test: {otp}")
    
    await redis.close()

if __name__ == "__main__":
    asyncio.run(test_redis())
