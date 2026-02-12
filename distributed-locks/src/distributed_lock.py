"""
Distributed Lock Implementation

Provides distributed mutual exclusion primitives for
coordinating access to shared resources.
"""

import time
import uuid
import threading
import logging
from typing import Optional, List, Dict, Set

# Import sub-modules
try:
    from src.fencing_tokens import FencingToken, FencedLock
    from src.deadlock_detector import DeadlockDetector
    from src.redlock import Redlock
    from src.lease_lock import LeaseLock
except ImportError:
    # For relative imports when running directly
    from fencing_tokens import FencingToken, FencedLock
    from deadlock_detector import DeadlockDetector
    from redlock import Redlock
    from lease_lock import LeaseLock

logger = logging.getLogger(__name__)

class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired"""
    pass

class LockTimeout(Exception):
    """Raised when lock acquisition times out"""
    pass


class DistributedLock:
    """
    Distributed lock with automatic expiration and ownership tracking.
    """
    
    def __init__(
        self,
        key: str,
        servers: List[str] = None,
        ttl_sec: float = 10,
        timeout_sec: float = 5,
        retry_delay: float = 0.1
    ):
        self.key = key
        self.servers = servers or []
        self.ttl_sec = ttl_sec
        self.timeout_sec = timeout_sec
        self.retry_delay = retry_delay
        
        # Internal state
        self._owner: Optional[str] = None
        self._token: Optional[str] = None  # Unique acquisition token
        self._expiry_time: float = 0.0
        self._mutex = threading.RLock() 
        
    def acquire(self, owner: str = None, timeout_sec: float = None, blocking: bool = True, ttl_sec: float = None) -> bool:
        """
        Acquire the lock.
        
        Args:
            owner: ID of the owner acquiring the lock.
            timeout_sec: Max time to wait.
            blocking: If False, return False immediately if not available.
            ttl_sec: Override default TTL for this acquisition.
        """
        if owner is None:
            owner = str(uuid.uuid4())
            
        if timeout_sec is None:
            timeout_sec = self.timeout_sec
            
        if not blocking:
            timeout_sec = 0
            
        effective_ttl = ttl_sec if ttl_sec is not None else self.ttl_sec
            
        start_time = time.time()
        
        while True:
            with self._mutex:
                now = time.time()
                
                # Check if currently locked
                if self._owner is not None:
                    # Check if expired
                    if now >= self._expiry_time:
                        self._owner = None
                        self._token = None
                    elif self._owner == owner:
                        # Re-entrant: extend
                        self._expiry_time = now + effective_ttl
                        return True
                
                # Try to acquire
                if self._owner is None:
                    self._owner = owner
                    self._token = str(uuid.uuid4()) # Generate unique token
                    self._expiry_time = now + effective_ttl
                    return True
            
            # Check timeout
            if time.time() - start_time >= timeout_sec:
                return False
                
            time.sleep(self.retry_delay)

    def release(self, owner: str = None, token: str = None):
        """
        Release the lock.
        Must provide either owner or token to verify.
        """
        with self._mutex:
            if self._owner is None:
                return # Already released or expired
            
            # Verify ownership
            if owner is not None and self._owner != owner:
                raise LockAcquisitionError(f"Cannot release lock owned by {self._owner} (requester: {owner})")
            
            if token is not None and self._token != token:
                raise LockAcquisitionError("Invalid token for release")
                
            self._owner = None
            self._token = None
            self._expiry_time = 0.0

    def renew(self, owner: str = None, ttl_sec: float = None) -> bool:
        """Renew the lock TTL."""
        with self._mutex:
            if self._owner is None:
                return False
            
            if owner is not None and self._owner != owner:
                return False
                
            ttl = ttl_sec if ttl_sec is not None else self.ttl_sec
            self._expiry_time = time.time() + ttl
            return True

    def get_owner(self) -> Optional[str]:
        """Get current owner."""
        with self._mutex:
            if self._owner is None:
                return None
            if time.time() >= self._expiry_time:
                self._owner = None
                self._token = None
                return None
            return self._owner
            
    def get_token(self) -> Optional[str]:
        """Get current token."""
        with self._mutex:
            self.get_owner() # Trigger expiry check
            return self._token

    def is_held(self) -> bool:
        """Check if lock is held."""
        return self.get_owner() is not None

    def try_lock(self, owner: str = None, timeout_sec: float = 0) -> bool:
        """Try to acquire lock with optional timeout."""
        return self.acquire(owner=owner, timeout_sec=timeout_sec)
        
    def time_remaining(self) -> float:
        with self._mutex:
            if self._owner is None:
                return 0.0
            remaining = self._expiry_time - time.time()
            return max(0.0, remaining)
            
    # Context manager support
    def __enter__(self):
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class LockManager:
    """
    Manages multiple named locks.
    """
    def __init__(self):
        self._locks: Dict[str, DistributedLock] = {}
        self._lock_mutex = threading.Lock()
        
    def get_lock(self, resource: str) -> DistributedLock:
        with self._lock_mutex:
            if resource not in self._locks:
                self._locks[resource] = DistributedLock(key=resource)
            return self._locks[resource]

    def acquire_lock(self, resource: str, owner: str = None, timeout_sec: float = 10) -> Optional[str]:
        """
        Acquire a lock for a resource.
        Returns the unique lock token if successful, None otherwise.
        """
        lock = self.get_lock(resource)
        if owner is None:
            owner = str(uuid.uuid4())
            
        if lock.acquire(owner=owner, timeout_sec=timeout_sec):
            return lock.get_token()
        return None

    def release_lock(self, resource: str, token: str):
        """Release a lock using the token."""
        lock = self.get_lock(resource)
        try:
            lock.release(token=token)
        except LockAcquisitionError:
            pass # Ignore if already released

    def get_locks_held(self, owner: str) -> List[str]:
        """Get list of resources held by owner."""
        held = []
        with self._lock_mutex:
            for resource, lock in self._locks.items():
                if lock.get_owner() == owner:
                    held.append(resource)
        return held


if __name__ == "__main__":
    print("=== Distributed Lock Module ===")
    lock = DistributedLock("test")
    if lock.acquire(owner="me"):
        print("Acquired!")
        print(f"Token: {lock.get_token()}")
        lock.release(owner="me")
