"""
Lease-based Lock Implementation

Implements time-bounded locks that automatically expire (leases).
"""

import time
import threading
from typing import Optional, Any

class LeaseLock:
    """
    A lock that is valid for a specific duration (lease).
    """
    
    def __init__(self, resource: str, duration: float, coordinator: Any = None):
        """
        Args:
            resource: Resource name
            duration: Lease duration in seconds
            coordinator: Optional coordinator backend (e.g. ZooKeeper client)
        """
        self.resource = resource
        self.duration = duration
        self.coordinator = coordinator
        
        self.acquired = False
        self.expiry_time = 0.0
        self._lock = threading.Lock()
        
    def acquire(self) -> bool:
        """Acquire the lease."""
        with self._lock:
            now = time.time()
            # If we already hold it and it hasn't expired
            if self.acquired and now < self.expiry_time:
                return True
            
            # Simulate acquisition (or use coordinator)
            # In a real system: coordinator.create_ephemeral(path, ttl=duration)
            self.acquired = True
            self.expiry_time = now + self.duration
            return True

    def release(self):
        """Release the lease explicitly."""
        with self._lock:
            self.acquired = False
            self.expiry_time = 0.0

    def renew(self) -> bool:
        """Extend the lease."""
        with self._lock:
            if not self.acquired:
                return False
            
            # Check if already expired
            if time.time() >= self.expiry_time:
                self.acquired = False
                return False
                
            self.expiry_time = time.time() + self.duration
            return True

    def time_remaining(self) -> float:
        """Return time remaining in seconds."""
        with self._lock:
            if not self.acquired:
                return 0.0
            remaining = self.expiry_time - time.time()
            return max(0.0, remaining)
            
    def is_valid(self) -> bool:
        return self.time_remaining() > 0
