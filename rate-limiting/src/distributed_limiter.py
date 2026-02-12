"""
Distributed Rate Limiting

Redis-based rate limiting implementation.
"""

import time
from typing import Optional

try:
    import redis
except ImportError:
    redis = None

class RedisRateLimiter:
    """
    Distributed Rate Limiter using Redis
    
    Implements sliding window algorithm using Redis Sorted Sets (ZSET).
    Ensures atomicity using Lua scripts.
    """
    
    # Lua script for sliding window
    # KEYS[1]: Rate limit key
    # ARGV[1]: Window size in seconds
    # ARGV[2]: Max requests
    # ARGV[3]: Current timestamp
    LUA_SCRIPT = """
    local key = KEYS[1]
    local window = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    
    -- Remove old requests
    local clear_before = now - window
    redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
    
    -- Count current requests
    local count = redis.call('ZCARD', key)
    
    if count < limit then
        -- Add new request
        redis.call('ZADD', key, now, now)
        -- Set expiry (window + 1 second to be safe)
        redis.call('EXPIRE', key, window + 1)
        return 1
    else
        return 0
    end
    """
    
    def __init__(self, redis_client, key_prefix: str = "ratelimit"):
        """
        Initialize Redis rate limiter
        
        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
        """
        if redis is None and redis_client is None:
             raise ImportError("Redis client required. Install 'redis' package.")
             
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.script = self.redis.register_script(self.LUA_SCRIPT)
    
    def allow_request(self, key: str, max_requests: int, window: int) -> bool:
        """
        Check if request is allowed
        
        Args:
            key: Unique identifier (e.g., user_id)
            max_requests: Maximum requests allowed in window
            window: Time window in seconds
            
        Returns:
            True if allowed, False if rate limited
        """
        full_key = f"{self.key_prefix}:{key}"
        now = time.time()
        
        result = self.script(
            keys=[full_key],
            args=[window, max_requests, now]
        )
        
        return bool(result)

    def get_remaining(self, key: str, max_requests: int, window: int) -> int:
        """
        Get remaining requests allowed
        
        Args:
            key: Unique identifier
            max_requests: Max requests
            window: Time window
            
        Returns:
            Number of remaining requests allowed
        """
        full_key = f"{self.key_prefix}:{key}"
        now = time.time()
        
        # We assume this doesn't need to be perfectly atomic with the check
        # But to be accurate, we should probably clean first
        pipeline = self.redis.pipeline()
        pipeline.zremrangebyscore(full_key, 0, now - window)
        pipeline.zcard(full_key)
        results = pipeline.execute()
        
        current_count = results[1]
        return max(0, max_requests - current_count)
