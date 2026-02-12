import unittest
from unittest.mock import MagicMock, patch
import time
from src.distributed_limiter import RedisRateLimiter

class MockRedis:
    def __init__(self):
        self.data = {}  # key -> list of (score, member)
        self.pipeline_results = []

    def register_script(self, script):
        return MockScript(self)

    def pipeline(self):
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        if key not in self.data:
            res = 0
        else:
            original_len = len(self.data[key])
            self.data[key] = [
                (s, m) for s, m in self.data[key] 
                if not (min_score <= s <= max_score)
            ]
            res = original_len - len(self.data[key])
        self.pipeline_results.append(res)
        return self

    def zcard(self, key):
        if key not in self.data:
            res = 0
        else:
            res = len(self.data[key])
        self.pipeline_results.append(res)
        return self
        
    def execute(self):
        res = self.pipeline_results
        self.pipeline_results = []
        return res

class MockScript:
    def __init__(self, redis):
        self.redis = redis
    
    def __call__(self, keys, args):
        key = keys[0]
        window = float(args[0])
        limit = int(args[1])
        now = float(args[2])
        
        # ZREMRANGEBYSCORE
        clear_before = now - window
        if key in self.redis.data:
            self.redis.data[key] = [
                (s, m) for s, m in self.redis.data[key]
                if s > clear_before
            ]
        
        # ZCARD
        count = len(self.redis.data.get(key, []))
        
        if count < limit:
            # ZADD
            if key not in self.redis.data:
                self.redis.data[key] = []
            self.redis.data[key].append((now, now))
            return 1
        else:
            return 0

class TestRedisRateLimiter(unittest.TestCase):
    def setUp(self):
        self.mock_redis = MockRedis()
        self.limiter = RedisRateLimiter(self.mock_redis)

    def test_allow_request(self):
        allowed = self.limiter.allow_request("user1", 10, 60)
        self.assertTrue(allowed)

    def test_rate_limit(self):
        # Max 2 requests
        self.assertTrue(self.limiter.allow_request("user2", 2, 60))
        self.assertTrue(self.limiter.allow_request("user2", 2, 60))
        self.assertFalse(self.limiter.allow_request("user2", 2, 60))

    @patch('time.time')
    def test_window_expiry(self, mock_time):
        mock_time.return_value = 100.0
        
        # Max 1 request per 1 second
        self.assertTrue(self.limiter.allow_request("user3", 1, 1))
        self.assertFalse(self.limiter.allow_request("user3", 1, 1))
        
        # Advance time by 1.1 seconds
        mock_time.return_value = 101.1
        self.assertTrue(self.limiter.allow_request("user3", 1, 1))

    @patch('time.time')
    def test_get_remaining(self, mock_time):
        mock_time.return_value = 1000.0
        self.limiter.allow_request("user4", 5, 60)
        self.limiter.allow_request("user4", 5, 60)
        
        remaining = self.limiter.get_remaining("user4", 5, 60)
        self.assertEqual(remaining, 3)

if __name__ == '__main__':
    unittest.main()