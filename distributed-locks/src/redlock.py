"""
Redlock Implementation

Implements the Redlock algorithm for distributed locking with Redis.
Reference: https://redis.io/topics/distlock
"""

import time
import uuid
import logging
from typing import List, Optional

# Try to import redis, but don't fail if not present
try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class Redlock:
    """
    Redlock distributed lock implementation.
    
    Requires a quorum (N/2 + 1) of Redis instances to acquire lock.
    """
    
    def __init__(self, resource: str, servers: List[str], ttl: int = 10000, retry_count: int = 3, retry_delay: float = 0.2):
        """
        Initialize Redlock
        
        Args:
            resource: Resource name to lock
            servers: List of Redis URIs (e.g. "redis://localhost:6379")
            ttl: Time-to-live in milliseconds
            retry_count: Number of retries
            retry_delay: Delay between retries in seconds
        """
        self.resource = resource
        self.servers = []
        self.quorum = 0
        self.ttl = ttl
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.token = None
        
        if redis:
            for server_uri in servers:
                try:
                    self.servers.append(redis.from_url(server_uri))
                except Exception as e:
                    logger.warning(f"Failed to connect to Redis at {server_uri}: {e}")
            
            self.quorum = (len(self.servers) // 2) + 1
        else:
            logger.warning("Redis library not installed. Redlock will not function correctly.")

    def acquire(self) -> bool:
        """
        Acquire the lock.
        """
        if not self.servers:
            return False
            
        self.token = str(uuid.uuid4())
        
        for attempt in range(self.retry_count):
            start_time = int(time.time() * 1000)
            n_acquired = 0
            
            for server in self.servers:
                try:
                    # SET resource token NX PX ttl
                    if server.set(self.resource, self.token, nx=True, px=self.ttl):
                        n_acquired += 1
                except Exception:
                    continue
            
            elapsed = int(time.time() * 1000) - start_time
            validity = self.ttl - elapsed - 200 # 200ms drift allowance
            
            if n_acquired >= self.quorum and validity > 0:
                return True
            else:
                # Failed to acquire quorum, unlock all
                self.release()
                
            # Wait before retry
            time.sleep(self.retry_delay) # randomised delay recommended in paper
            
        return False

    def release(self):
        """
        Release the lock on all instances.
        """
        # Lua script to release only if token matches
        unlock_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        for server in self.servers:
            try:
                server.eval(unlock_script, 1, self.resource, self.token)
            except Exception:
                pass
        
        self.token = None
