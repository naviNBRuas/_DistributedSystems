from typing import Dict, Any, Optional
import json
from crdt_base import CRDT


class CausalContext(CRDT):
    """
    Vector Clock for Causal Context tracking.
    
    State: Map of node_id -> counter.
    Operations: increment.
    Merge: Element-wise max.
    Query: Compare clocks.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock: Dict[str, int] = {node_id: 0}
        
    def increment(self) -> None:
        """Increment this node's clock."""
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
        
    def update(self, other_clock: Dict[str, int]) -> None:
        """Update context with another clock (without full merge)."""
        for node, count in other_clock.items():
            self.clock[node] = max(self.clock.get(node, 0), count)
            
    def value(self) -> Dict[str, int]:
        """Get current vector clock."""
        return self.clock.copy()
        
    def merge(self, other: 'CausalContext') -> None:
        """Merge with another Vector Clock."""
        if not isinstance(other, CausalContext):
            raise TypeError("Cannot merge with non-CausalContext")
        self.update(other.clock)
        
    def compare(self, other: 'CausalContext') -> str:
        """
        Compare with another Vector Clock.
        Returns: 'less', 'greater', 'equal', 'concurrent'
        """
        less = False
        greater = False
        
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        
        for node in all_nodes:
            c1 = self.clock.get(node, 0)
            c2 = other.clock.get(node, 0)
            
            if c1 < c2:
                less = True
            elif c1 > c2:
                greater = True
                
        if less and greater:
            return 'concurrent'
        elif less:
            return 'less'
        elif greater:
            return 'greater'
        else:
            return 'equal'

    def to_json(self) -> str:
        return json.dumps({
            'node_id': self.node_id,
            'clock': self.clock
        })
        
    @classmethod
    def from_json(cls, json_str: str) -> 'CausalContext':
        data = json.loads(json_str)
        cc = cls(data['node_id'])
        cc.clock = data['clock']
        return cc
        
    def __repr__(self) -> str:
        return f"VectorClock({self.clock})"
