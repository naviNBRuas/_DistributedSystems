"""
Rate Limiting Algorithms

Token bucket, leaky bucket, and sliding window implementations
for traffic control and throttling.
"""

import time
import threading
import math
from typing import Optional, Dict
from enum import Enum


class TokenBucketLimiter:
    """
    Token Bucket Rate Limiter
    
    Implements token bucket algorithm:
    - Tokens accumulate at fixed rate
    - Requests consume tokens
    - Allows bursts up to bucket capacity
    """
    
    def __init__(self, rate: float, capacity: float, refill_interval: float = 1.0):
        """
        Initialize token bucket limiter
        
        Args:
            rate: Tokens generated per refill_interval
            capacity: Maximum tokens in bucket
            refill_interval: Time interval for refill (seconds)
        """
        self.rate = rate
        self.capacity = capacity
        self.refill_interval = refill_interval
        
        self.tokens = capacity  # Start with full bucket
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
        self.stats = {
            "requests": 0,
            "allowed": 0,
            "rejected": 0
        }
    
    def allow_request(self, tokens: float = 1.0) -> bool:
        """
        Check if request is allowed
        
        Args:
            tokens: Number of tokens to consume (default 1)
            
        Returns:
            True if request allowed, False if rate limited
        """
        with self.lock:
            # Refill tokens
            self._refill()
            
            self.stats["requests"] += 1
            
            # Check if enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.stats["allowed"] += 1
                return True
            else:
                self.stats["rejected"] += 1
                return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        intervals = elapsed / self.refill_interval
        tokens_to_add = intervals * self.rate
        
        # Add tokens up to capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            return {
                "requests": self.stats["requests"],
                "allowed": self.stats["allowed"],
                "rejected": self.stats["rejected"],
                "current_tokens": self.tokens,
                "rejection_rate": (
                    self.stats["rejected"] / self.stats["requests"]
                    if self.stats["requests"] > 0 else 0
                )
            }


class LeakyBucketLimiter:
    """
    Leaky Bucket Rate Limiter
    
    Implements leaky bucket algorithm:
    - Requests added to queue
    - Queue processed at fixed rate
    - Provides smooth rate limiting
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize leaky bucket limiter
        
        Args:
            rate: Requests per second to process
            capacity: Maximum queue size
        """
        self.rate = rate
        self.capacity = capacity
        self.interval = 1.0 / rate  # Time between processing
        
        self.queue = []
        self.last_process = time.time()
        self.lock = threading.Lock()
        
        self.stats = {
            "requests": 0,
            "processed": 0,
            "dropped": 0
        }
    
    def allow_request(self) -> bool:
        """
        Check if request can be queued
        
        Returns:
            True if request queued, False if bucket full (dropped)
        """
        with self.lock:
            self._leak()
            
            self.stats["requests"] += 1
            
            # Check queue capacity
            if len(self.queue) < self.capacity:
                self.queue.append(time.time())
                return True
            else:
                self.stats["dropped"] += 1
                return False
    
    def _leak(self):
        """Process items from queue at fixed rate"""
        now = time.time()
        
        while self.queue and (now - self.last_process) >= self.interval:
            self.queue.pop(0)
            self.last_process += self.interval
            self.stats["processed"] += 1
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            return {
                "requests": self.stats["requests"],
                "processed": self.stats["processed"],
                "dropped": self.stats["dropped"],
                "queue_size": len(self.queue),
                "drop_rate": (
                    self.stats["dropped"] / self.stats["requests"]
                    if self.stats["requests"] > 0 else 0
                )
            }


class SlidingWindowLimiter:
    """
    Sliding Window Rate Limiter
    
    Implements sliding window algorithm:
    - Tracks requests in time window
    - Exact rate limiting
    - Per-unit tracking (e.g., per-user)
    """
    
    def __init__(self, window_size: float, max_requests: int):
        """
        Initialize sliding window limiter
        
        Args:
            window_size: Time window in seconds
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        
        self.requests: Dict[str, list] = {}  # unit_id -> list of timestamps
        self.lock = threading.Lock()
    
    def allow_request(self, unit_id: str = "default") -> bool:
        """
        Check if request allowed for unit
        
        Args:
            unit_id: Unit identifier (e.g., user_id, IP)
            
        Returns:
            True if request allowed
        """
        with self.lock:
            now = time.time()
            window_start = now - self.window_size
            
            # Get or create request list for unit
            if unit_id not in self.requests:
                self.requests[unit_id] = []
            
            # Remove old requests outside window
            self.requests[unit_id] = [
                ts for ts in self.requests[unit_id]
                if ts > window_start
            ]
            
            # Check if at limit
            if len(self.requests[unit_id]) < self.max_requests:
                self.requests[unit_id].append(now)
                return True
            else:
                return False
    
    def get_remaining(self, unit_id: str = "default") -> int:
        """Get remaining requests in current window"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_size
            
            if unit_id not in self.requests:
                return self.max_requests
            
            # Count requests in window
            current = sum(
                1 for ts in self.requests[unit_id]
                if ts > window_start
            )
            
            return max(0, self.max_requests - current)


class AdaptiveRateLimiter:
    """
    Adaptive Rate Limiter
    
    Automatically adjusts rate based on system load
    """
    
    def __init__(self, base_rate: float, min_rate: float = 0.1, max_rate: float = None):
        """
        Initialize adaptive rate limiter
        
        Args:
            base_rate: Base request rate
            min_rate: Minimum allowed rate
            max_rate: Maximum allowed rate
        """
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.min_rate = min_rate
        self.max_rate = max_rate or (base_rate * 10)
        
        self.limiter = TokenBucketLimiter(
            rate=self.current_rate,
            capacity=self.current_rate * 2
        )
        self.lock = threading.Lock()
    
    def adjust_rate(self, load_factor: float):
        """
        Adjust rate based on load
        
        Args:
            load_factor: Load percentage (0.0 to 1.0)
        """
        with self.lock:
            # Adjust rate based on load
            if load_factor > 0.9:
                # High load: reduce rate
                self.current_rate = max(
                    self.min_rate,
                    self.current_rate * 0.9
                )
            elif load_factor < 0.5:
                # Low load: increase rate
                self.current_rate = min(
                    self.max_rate,
                    self.current_rate * 1.1
                )
            
            # Update limiter
            self.limiter.rate = self.current_rate
    
    def allow_request(self) -> bool:
        """Check if request allowed"""
        return self.limiter.allow_request()


# Example usage
if __name__ == "__main__":
    print("=== Rate Limiting Examples ===\n")
    
    # Token bucket
    print("--- Token Bucket Limiter ---")
    tb = TokenBucketLimiter(rate=10, capacity=20)
    
    # Make requests
    for i in range(25):
        allowed = tb.allow_request()
        status = "✓" if allowed else "✗"
        print(f"Request {i+1}: {status}")
    
    stats = tb.get_stats()
    print(f"Stats: {stats}\n")
    
    # Leaky bucket
    print("--- Leaky Bucket Limiter ---")
    lb = LeakyBucketLimiter(rate=5, capacity=10)
    
    for i in range(15):
        allowed = lb.allow_request()
        status = "✓" if allowed else "✗"
        print(f"Request {i+1}: {status}")
    
    stats = lb.get_stats()
    print(f"Stats: {stats}\n")
    
    # Sliding window
    print("--- Sliding Window Limiter ---")
    sw = SlidingWindowLimiter(window_size=10, max_requests=5)
    
    for i in range(8):
        allowed = sw.allow_request("user_123")
        status = "✓" if allowed else "✗"
        remaining = sw.get_remaining("user_123")
        print(f"Request {i+1}: {status} (remaining: {remaining})")
