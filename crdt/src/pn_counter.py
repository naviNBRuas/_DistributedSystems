"""
PN-Counter (Positive-Negative Counter) CRDT

A counter supporting both increments and decrements.
Implemented using two G-Counters (positive and negative).
"""

from typing import Dict
import json
from crdt_base import CRDT
from g_counter import GCounter


class PNCounter(CRDT):
    """
    Positive-Negative Counter CRDT
    
    State: Two G-Counters (P and N)
    Operations: increment, decrement
    Query: P.value() - N.value()
    
    Properties:
    - Supports both increment and decrement
    - Eventually consistent
    - Commutative merge
    """
    
    def __init__(self, node_id: str):
        """
        Initialize PN-Counter
        
        Args:
            node_id: Unique identifier for this replica
        """
        self.node_id = node_id
        self.positive = GCounter(node_id)  # Increments
        self.negative = GCounter(node_id)  # Decrements
    
    def increment(self, value: int = 1):
        """
        Increment counter
        
        Args:
            value: Amount to increment (default 1)
        """
        if value < 0:
            raise ValueError("Increment value must be positive")
        self.positive.increment(value)
    
    def decrement(self, value: int = 1):
        """
        Decrement counter
        
        Args:
            value: Amount to decrement (default 1)
        """
        if value < 0:
            raise ValueError("Decrement value must be positive")
        self.negative.increment(value)
    
    def value(self) -> int:
        """
        Get current counter value
        
        Returns:
            P - N (positive minus negative)
        """
        return self.positive.value() - self.negative.value()
    
    def merge(self, other: 'PNCounter'):
        """
        Merge with another PN-Counter
        
        Args:
            other: Another PN-Counter to merge with
        """
        if not isinstance(other, PNCounter):
            raise TypeError("Cannot merge with non-PNCounter")
            
        self.positive.merge(other.positive)
        self.negative.merge(other.negative)
    
    def get_state(self) -> Dict:
        """Get current state for replication"""
        return {
            'positive': self.positive.get_state(),
            'negative': self.negative.get_state()
        }
    
    def set_state(self, state: Dict):
        """Set state from replication"""
        self.positive.set_state(state['positive'])
        self.negative.set_state(state['negative'])
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps({
            'node_id': self.node_id,
            'positive': self.positive.get_state(),
            'negative': self.negative.get_state()
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PNCounter':
        """Deserialize from JSON"""
        data = json.loads(json_str)
        counter = cls(data['node_id'])
        counter.positive.set_state(data['positive'])
        counter.negative.set_state(data['negative'])
        return counter
    
    def __repr__(self):
        return f"PNCounter(node={self.node_id}, value={self.value()})"


# Example usage
if __name__ == "__main__":
    print("=== PN-Counter CRDT Example ===\n")
    
    # Create two replicas
    counter1 = PNCounter(node_id="node1")
    counter2 = PNCounter(node_id="node2")
    
    # Node 1: increment and decrement
    print("--- Node 1 Operations ---")
    counter1.increment(10)
    counter1.decrement(3)
    print(f"Node 1: {counter1.value()}")  # 7
    
    # Node 2: different operations
    print("\n--- Node 2 Operations ---")
    counter2.increment(5)
    counter2.decrement(2)
    print(f"Node 2: {counter2.value()}")  # 3
    
    # Merge
    print("\n--- Merge ---")
    counter1.merge(counter2)
    counter2.merge(counter1)
    
    print(f"Node 1 after merge: {counter1.value()}")  # 10
    print(f"Node 2 after merge: {counter2.value()}")  # 10
    
    # Demonstrate convergence
    print("\n--- Convergence ---")
    c1 = PNCounter("a")
    c2 = PNCounter("b")
    
    # Concurrent operations
    c1.increment(100)
    c2.decrement(50)
    
    # Bidirectional merge
    c1.merge(c2)
    c2.merge(c1)
    
    print(f"Replica A: {c1.value()}")
    print(f"Replica B: {c2.value()}")
    print(f"Converged: {c1.value() == c2.value()}")
