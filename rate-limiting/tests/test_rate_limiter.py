import unittest
import time
import threading
from src.rate_limiter import (
    TokenBucketLimiter,
    LeakyBucketLimiter,
    SlidingWindowLimiter,
    AdaptiveRateLimiter
)

class TestTokenBucketLimiter(unittest.TestCase):
    def test_initialization(self):
        limiter = TokenBucketLimiter(rate=10, capacity=20)
        self.assertEqual(limiter.rate, 10)
        self.assertEqual(limiter.capacity, 20)
        self.assertEqual(limiter.tokens, 20)

    def test_allow_request(self):
        limiter = TokenBucketLimiter(rate=10, capacity=10)
        self.assertTrue(limiter.allow_request())
        self.assertEqual(limiter.tokens, 9)

    def test_capacity_limit(self):
        limiter = TokenBucketLimiter(rate=10, capacity=2)
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())
        self.assertFalse(limiter.allow_request())

    def test_refill(self):
        limiter = TokenBucketLimiter(rate=10, capacity=10, refill_interval=0.1)
        # Consume all tokens
        for _ in range(10):
            limiter.allow_request()
        self.assertFalse(limiter.allow_request())
        
        # Wait for refill (0.1s should give 1 token)
        time.sleep(0.15)
        self.assertTrue(limiter.allow_request())

class TestLeakyBucketLimiter(unittest.TestCase):
    def test_initialization(self):
        limiter = LeakyBucketLimiter(rate=10, capacity=5)
        self.assertEqual(limiter.rate, 10)
        self.assertEqual(limiter.capacity, 5)

    def test_queueing(self):
        limiter = LeakyBucketLimiter(rate=1, capacity=2)
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())
        self.assertFalse(limiter.allow_request())

    def test_leaking(self):
        limiter = LeakyBucketLimiter(rate=10, capacity=2)
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())
        self.assertFalse(limiter.allow_request())
        
        # Wait for leak (0.1s for 10/s rate means 1 item processed)
        time.sleep(0.15)
        self.assertTrue(limiter.allow_request())

class TestSlidingWindowLimiter(unittest.TestCase):
    def test_window(self):
        limiter = SlidingWindowLimiter(window_size=0.2, max_requests=2)
        self.assertTrue(limiter.allow_request("u1"))
        self.assertTrue(limiter.allow_request("u1"))
        self.assertFalse(limiter.allow_request("u1"))
        
        time.sleep(0.3)
        self.assertTrue(limiter.allow_request("u1"))

    def test_multiple_units(self):
        limiter = SlidingWindowLimiter(window_size=1, max_requests=1)
        self.assertTrue(limiter.allow_request("u1"))
        self.assertFalse(limiter.allow_request("u1"))
        self.assertTrue(limiter.allow_request("u2"))

class TestAdaptiveRateLimiter(unittest.TestCase):
    def test_adaptation(self):
        limiter = AdaptiveRateLimiter(base_rate=10, min_rate=5, max_rate=20)
        
        # High load
        limiter.adjust_rate(0.95)
        self.assertLess(limiter.current_rate, 10)
        
        # Reset
        limiter.current_rate = 10
        limiter.limiter.rate = 10
        
        # Low load
        limiter.adjust_rate(0.4)
        self.assertGreater(limiter.current_rate, 10)

if __name__ == '__main__':
    unittest.main()
