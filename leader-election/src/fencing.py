"""
Fencing Tokens for Split-Brain Prevention

Provides monotonically increasing tokens that prevent
stale leaders from performing operations.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class FencingToken:
    """
    Token that represents a leadership epoch
    
    Each leader gets a token with a monotonically increasing epoch.
    Operations using stale tokens are rejected.
    """
    node_id: str
    epoch: int  # Monotonically increasing
    expiration: Optional[float] = None  # Unix timestamp
    
    def is_valid(self) -> bool:
        """Check if token is still valid"""
        if self.expiration is None:
            return True
        return time.time() < self.expiration
    
    def get_epoch(self) -> int:
        """Get the epoch number"""
        return self.epoch
    
    def __repr__(self):
        return f"FencingToken(node={self.node_id}, epoch={self.epoch})"
    
    def __lt__(self, other):
        """Compare tokens by epoch"""
        if not isinstance(other, FencingToken):
            return NotImplemented
        return self.epoch < other.epoch
    
    def __eq__(self, other):
        """Check token equality"""
        if not isinstance(other, FencingToken):
            return NotImplemented
        return self.epoch == other.epoch and self.node_id == other.node_id


class FencingTokenManager:
    """
    Manages fencing tokens for a cluster
    
    Ensures monotonically increasing epoch numbers and
    validates tokens for operations.
    """
    
    def __init__(self):
        self.current_epoch = 0
        self.current_token: Optional[FencingToken] = None
    
    def issue_token(self, node_id: str, duration: Optional[float] = None) -> FencingToken:
        """
        Issue a new fencing token
        
        Args:
            node_id: Node becoming leader
            duration: Token validity duration (seconds)
            
        Returns:
            New fencing token with incremented epoch
        """
        self.current_epoch += 1
        
        expiration = None
        if duration:
            expiration = time.time() + duration
        
        token = FencingToken(
            node_id=node_id,
            epoch=self.current_epoch,
            expiration=expiration
        )
        
        self.current_token = token
        return token
    
    def validate_token(self, token: FencingToken) -> bool:
        """
        Validate a token for an operation
        
        Returns True if token is current and valid
        """
        if not token.is_valid():
            return False
        
        if self.current_token is None:
            return False
        
        # Token must match current epoch
        return token.epoch == self.current_token.epoch
    
    def get_current_epoch(self) -> int:
        """Get current epoch number"""
        return self.current_epoch
