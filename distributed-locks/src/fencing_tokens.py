"""
Fencing Tokens Implementation

Provides monotonically increasing tokens to prevent stale lock holders
from accessing shared resources.
"""

import threading
import time
from functools import total_ordering


@total_ordering
class FencingToken:
    """
    Manages monotonically increasing fencing tokens.
    """
    _lock = threading.Lock()
    _counter = 0

    @classmethod
    def generate(cls) -> 'FencingToken':
        """
        Generate a new monotonically increasing token.
        
        In a distributed system, this would typically come from the
        coordination service (e.g., ZooKeeper zxid, Etcd revision).
        Here we simulate it with a thread-safe counter.
        """
        with cls._lock:
            cls._counter += 1
            return cls(cls._counter)

    @staticmethod
    def validate(token_offered, current_token) -> bool:
        """
        Validate if the offered token is valid against the current system state.
        
        Args:
            token_offered: The token provided by the client
            current_token: The current highest token seen by the resource
            
        Returns:
            True if token_offered >= current_token (or whatever the validity logic is)
            Usually, strictly greater is not required if we are just checking valid ownership,
            but for "fencing" against OLD holders, we reject if token_offered < current_token.
        """
        if token_offered is None or current_token is None:
            return False
        return token_offered >= current_token

    def __init__(self, value: int):
        self.value = value

    def __lt__(self, other):
        if isinstance(other, FencingToken):
            return self.value < other.value
        return self.value < other

    def __eq__(self, other):
        if isinstance(other, FencingToken):
            return self.value == other.value
        return self.value == other
    
    def __repr__(self):
        return f"FencingToken({self.value})"


class FencedLock:
    """
    A lock that returns a fencing token upon acquisition.
    """
    def __init__(self, lock_impl):
        self.lock = lock_impl
        self.token = None

    def acquire_with_token(self, **kwargs) -> FencingToken:
        """
        Acquire lock and return fencing token.
        """
        if self.lock.acquire(**kwargs):
            # In a real system, the backend returns the token/version
            self.token = FencingToken.generate()
            return self.token
        return None

    def release(self):
        self.lock.release()
