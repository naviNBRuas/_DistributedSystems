"""
G-Counter (Grow-Only Counter) CRDT

A monotonically increasing counter that only supports increments.
Replicas can independently increment and merge their states.
"""

from typing import Dict, Any
import json
from crdt_base import CRDT


class GCounter(CRDT):
    """
    Grow-Only Counter CRDT
    
    State: Map of node_id -> count
    Operations: increment
    Merge: Element-wise max
    Query: Sum of all counts
    
    Properties:
    - Commutative: merge order doesn't matter
    - Associative: grouping doesn't matter
    - Idempotent: merging same state multiple times is safe
    """
    
    def __init__(self, node_id: str):
        """
        Initialize G-Counter
        
        Args:
            node_id: Unique identifier for this replica
        """
        self.node_id = node_id
        self.counts: Dict[str, int] = {}
        self.counts[node_id] = 0
    
    def increment(self, value: int = 1):
        """
        Increment counter by value
        
        Args:
            value: Amount to increment (must be positive)
        """
        if value < 0:
            raise ValueError("G-Counter only supports positive increments")
        
        self.counts[self.node_id] = self.counts.get(self.node_id, 0) + value
    
    def value(self) -> int:
        """
        Get current counter value
        
        Returns:
            Sum of all node counts
        """
        return sum(self.counts.values())
    
    def merge(self, other: 'GCounter'):
        """
        Merge with another G-Counter
        
        Takes element-wise maximum of counts.
        
        Args:
            other: Another G-Counter to merge with
        """
        if not isinstance(other, GCounter):
            raise TypeError("Cannot merge with non-GCounter")
            
        # Merge all nodes from other counter
        for node_id, count in other.counts.items():
            current = self.counts.get(node_id, 0)
            self.counts[node_id] = max(current, count)
    
    def get_state(self) -> Dict[str, int]:
        """Get current state for replication"""
        return self.counts.copy()
    
    def set_state(self, state: Dict[str, int]):
        """Set state from replication"""
        self.counts = state.copy()
    
    def compare(self, other: 'GCounter') -> str:
        """
        Compare two counters
        
        Returns:
            'less': self < other
            'greater': self > other
            'equal': self == other
            'concurrent': incomparable
        """
        less = False
        greater = False
        
        all_nodes = set(self.counts.keys()) | set(other.counts.keys())
        
        for node_id in all_nodes:
            self_count = self.counts.get(node_id, 0)
            other_count = other.counts.get(node_id, 0)
            
            if self_count < other_count:
                less = True
            elif self_count > other_count:
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
        """Serialize to JSON"""
        return json.dumps({
            'node_id': self.node_id,
            'counts': self.counts
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GCounter':
        """Deserialize from JSON"""
        data = json.loads(json_str)
        counter = cls(data['node_id'])
        counter.counts = data['counts']
        return counter
    
    def __repr__(self):
        return f"GCounter(node={self.node_id}, value={self.value()})"


# Example usage
if __name__ == "__main__":
    print("=== G-Counter CRDT Example ===\n")
    
    # Create two replicas
    counter1 = GCounter(node_id="node1")
    counter2 = GCounter(node_id="node2")
    
    # Independent increments
    print("--- Independent Operations ---")
    counter1.increment(5)
    counter1.increment(3)
    print(f"Node 1: {counter1} -> {counter1.value()}")
    
    counter2.increment(10)
    print(f"Node 2: {counter2} -> {counter2.value()}")
    
    # Merge
    print("\n--- Merge ---")
    counter1.merge(counter2)
    print(f"After merge: {counter1} -> {counter1.value()}")  # 18
    
    # Idempotent merge
    print("\n--- Idempotent Merge ---")
    counter1.merge(counter2)  # Merge again
    print(f"After duplicate merge: {counter1} -> {counter1.value()}")  # Still 18
    
    # Commutative merge
    print("\n--- Commutative Merge ---")
    counter3 = GCounter("node3")
    counter4 = GCounter("node4")
    counter3.increment(1)
    counter4.increment(2)
    
    # Order 1: merge 3 then 4
    temp1 = GCounter("temp1")
    temp1.merge(counter3)
    temp1.merge(counter4)
    
    # Order 2: merge 4 then 3
    temp2 = GCounter("temp2")
    temp2.merge(counter4)
    temp2.merge(counter3)
    
    print(f"Merge order 1: {temp1.value()}")
    print(f"Merge order 2: {temp2.value()}")
    print(f"Commutative: {temp1.value() == temp2.value()}")
    
    # Comparison
    print("\n--- Comparison ---")
    c1 = GCounter("a")
    c1.increment(5)
    
    c2 = GCounter("a")
    c2.increment(3)
    
    print(f"c1 vs c2: {c1.compare(c2)}")  # greater
    
    # Serialization
    print("\n--- Serialization ---")
    counter5 = GCounter("node5")
    counter5.increment(100)
    
    json_str = counter5.to_json()
    print(f"JSON: {json_str}")
    
    restored = GCounter.from_json(json_str)
    print(f"Restored: {restored}")
