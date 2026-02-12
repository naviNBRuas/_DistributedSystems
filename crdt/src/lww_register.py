from typing import Any, Optional, Tuple
import json
import time
from crdt_base import CRDT


class LWWRegister(CRDT):
    """
    Last-Write-Wins Register CRDT.
    
    State: (value, timestamp, node_id).
    Operations: write (update value).
    Merge: Compare timestamps, then node_ids.
    Query: value.
    
    Ensures convergence by using a total ordering of updates based on 
    timestamps and node IDs (as tie-breaker).
    """
    
    def __init__(self, node_id: str, initial_value: Any = None, initial_ts: float = 0.0):
        """
        Initialize LWW-Register.
        
        Args:
            node_id: Unique identifier for this replica.
            initial_value: Initial value of the register.
            initial_ts: Initial timestamp.
        """
        self.node_id = node_id
        self._value = initial_value
        self._timestamp = initial_ts
        self._writer_node = node_id  # Node that wrote the current value
    
    def write(self, value: Any, timestamp: float = None) -> None:
        """
        Update the register value.
        
        Args:
            value: The new value.
            timestamp: The timestamp of the write. Defaults to current time.
        """
        if timestamp is None:
            timestamp = time.time()
            
        # We accept the write if it's newer than what we have, 
        # OR if it's same time but from a larger node_id (arbitrary tie breaker),
        # OR if it's our own write (local updates usually win unless we drifted back in time?)
        # Standard LWW checks against current state.
        
        if self._should_update(timestamp, self.node_id):
            self._value = value
            self._timestamp = timestamp
            self._writer_node = self.node_id
            
    def _should_update(self, other_ts: float, other_node: str) -> bool:
        """Determine if we should update based on timestamp and node ID."""
        if other_ts > self._timestamp:
            return True
        elif other_ts < self._timestamp:
            return False
        else:
            # Tie-breaking using node ID (lexicographical order)
            return other_node > self._writer_node

    def value(self) -> Any:
        """Get current value."""
        return self._value
    
    def merge(self, other: 'LWWRegister') -> None:
        """
        Merge with another LWW-Register.
        
        Args:
            other: Another LWW-Register to merge with.
        """
        if not isinstance(other, LWWRegister):
            raise TypeError("Cannot merge with non-LWWRegister")
            
        if self._should_update(other._timestamp, other._writer_node):
            self._value = other._value
            self._timestamp = other._timestamp
            self._writer_node = other._writer_node
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'node_id': self.node_id,
            'value': self._value,
            'timestamp': self._timestamp,
            'writer_node': self._writer_node
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LWWRegister':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        # We need to construct it carefully to restore state
        register = cls(data['node_id'])
        register._value = data['value']
        register._timestamp = data['timestamp']
        register._writer_node = data['writer_node']
        return register

    def __repr__(self) -> str:
        return f"LWWRegister(value={self._value}, ts={self._timestamp})"
