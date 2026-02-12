"""
Unified Election Manager

Provides a single interface for different election algorithms.
"""

import logging
from enum import Enum
from typing import Optional, Callable, List, Any
from transport import Transport
from bully_algorithm import BullyElection
from ring_algorithm import RingElection
from lease_algorithm import LeaseBasedElection
from fencing import FencingToken, FencingTokenManager

logger = logging.getLogger(__name__)

class Algorithm(str, Enum):
    """Supported election algorithms"""
    BULLY = "bully"
    RING = "ring"
    LEASE = "lease"


class ElectionManager:
    """
    Unified interface for leader election
    
    Abstracts the specific algorithm implementation and provides
    a consistent API for leader election functionality.
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        transport: Transport,
        algorithm: Algorithm = Algorithm.BULLY,
        **kwargs
    ):
        """
        Initialize election manager
        
        Args:
            node_id: This node's unique ID
            peers: List of peer node IDs
            transport: Transport implementation for message passing
            algorithm: Election algorithm to use
            **kwargs: Algorithm-specific parameters
        """
        self.node_id = node_id
        self.peers = peers
        self.transport = transport
        self.algorithm = algorithm
        self.fencing_manager = FencingTokenManager()
        
        # Create the appropriate election implementation
        if algorithm == Algorithm.BULLY:
            self.impl = BullyElection(node_id, peers, transport, **kwargs)
        elif algorithm == Algorithm.RING:
            self.impl = RingElection(node_id, peers, transport, **kwargs)
        elif algorithm == Algorithm.LEASE:
            self.impl = LeaseBasedElection(node_id, peers, transport, **kwargs)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        self._leader_change_callbacks = []
        
        # Hook up internal callback to refresh fencing tokens or handle state changes
        self.impl.on_leader_change(self._on_internal_leader_change)
    
    def start(self):
        """Start participating in elections"""
        logger.info(f"Starting ElectionManager ({self.algorithm}) for {self.node_id}")
        self.impl.start()
    
    def stop(self):
        """Stop participating"""
        logger.info(f"Stopping ElectionManager for {self.node_id}")
        self.impl.stop()
    
    def is_leader(self) -> bool:
        """Check if this node is the current leader"""
        return self.impl.is_leader()
    
    def get_leader(self) -> Optional[str]:
        """Get current leader ID"""
        return self.impl.get_leader()
    
    def trigger_election(self):
        """Manually trigger a new election"""
        self.impl.trigger_election()
    
    def on_leader_change(self, callback: Callable[[str], None]):
        """
        Register callback for leadership changes
        
        Args:
            callback: Function called with new leader ID
        """
        self._leader_change_callbacks.append(callback)
    
    def _on_internal_leader_change(self, new_leader: str):
        """Handle leader change internally"""
        # If we became leader, we might want to issue a new fencing token
        if new_leader == self.node_id:
            # We just became leader
            self.fencing_manager.issue_token(self.node_id)
            
        # Notify external listeners
        for callback in self._leader_change_callbacks:
            try:
                callback(new_leader)
            except Exception as e:
                logger.error(f"Error in user callback: {e}")

    def get_fencing_token(self) -> Optional[FencingToken]:
        """
        Get fencing token for leader operations.
        Returns None if not leader.
        """
        if not self.is_leader():
            return None
        
        # Return current token (or issue new one if expired?)
        # Ideally, we return the token for the current term/epoch.
        # Since our simplified FencingManager tracks current epoch, we use that.
        
        # Note: In a real system, the election algo should provide the term.
        # Here we bridge it.
        
        # Use the fencing manager to get/refresh token
        return self.fencing_manager.current_token
    
    def get_metrics(self) -> dict:
        """Get election metrics"""
        return {
            "node_id": self.node_id,
            "is_leader": self.is_leader(),
            "current_leader": self.get_leader(),
            "algorithm": self.algorithm.value,
            "peers": len(self.peers),
            "epoch": self.fencing_manager.get_current_epoch()
        }
