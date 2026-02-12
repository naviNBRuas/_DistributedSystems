"""
rate-limiting - DistributedSystems Module
Version: 0.1.0
"""

from .rate_limiter import (
    TokenBucketLimiter,
    LeakyBucketLimiter,
    SlidingWindowLimiter,
    AdaptiveRateLimiter
)

__all__ = [
    "TokenBucketLimiter",
    "LeakyBucketLimiter",
    "SlidingWindowLimiter",
    "AdaptiveRateLimiter"
]

try:
    from .distributed_limiter import RedisRateLimiter
    __all__.append("RedisRateLimiter")
except ImportError:
    # Redis might not be installed or configured
    pass

__version__ = "0.1.0"
