"""
Vector Clock Implementation

Provides causal ordering and concurrency detection
for events in distributed systems.
"""

from typing import Dict, List, Optional
from copy import deepcopy


class VectorClock:
    """
    Vector clock implementation for causality tracking
    
    Properties:
    - Can determine if events are causally related or concurrent
    - Each node maintains a vector of logical clocks (one per node)
    - Space complexity: O(N) where N is number of nodes
    
    Advantages over Lamport:
    - Can detect concurrent events
    - Provides causal ordering, not just total ordering
    """
    
    def __init__(self, node_id: str, peers: List[str]):
        """
        Initialize vector clock
        
        Args:
            node_id: This node's unique identifier
            peers: List of peer node IDs (not including self)
        """
        self.node_id = node_id
        self.peers = set(peers)
        
        # Initialize vector: {node_id: timestamp}
        all_nodes = {node_id} | self.peers
        self.vector: Dict[str, int] = {node: 0 for node in all_nodes}
    
    def tick(self) -> Dict[str, int]:
        """
        Increment clock for a local event
        
        Returns:
            Current vector clock state
        """
        self.vector[self.node_id] += 1
        return self.get_vector()
    
    def send(self) -> Dict[str, int]:
        """
        Prepare to send a message
        
        Increments local component and returns vector to attach to message.
        
        Returns:
            Vector clock snapshot to include with message
        """
        self.vector[self.node_id] += 1
        return self.get_vector()
    
    def receive(self, sender_id: str, message_vector: Dict[str, int]) -> Dict[str, int]:
        """
        Update clock upon receiving a message
        
        Updates each component to max(local, received) and increments own component.
        
        Args:
            sender_id: ID of the node that sent the message
            message_vector: Vector clock from the message
            
        Returns:
            Updated vector clock
        """
        # Update each component to max
        for node_id in self.vector:
            if node_id in message_vector:
                self.vector[node_id] = max(self.vector[node_id], message_vector[node_id])
        
        # Increment own component
        self.vector[self.node_id] += 1
        
        return self.get_vector()
    
    def get_vector(self) -> Dict[str, int]:
        """Get current vector clock (copy)"""
        return deepcopy(self.vector)
    
    def happened_before(self, other_vector: Dict[str, int]) -> bool:
        """
        Check if this clock happened before another
        
        Clock V1 happened before V2 if:
        - V1[i] <= V2[i] for all i
        - V1[i] < V2[i] for at least one i
        
        Args:
            other_vector: Another vector clock to compare
            
        Returns:
            True if this clock happened before other
        """
        at_least_one_less = False
        
        for node_id in self.vector:
            if node_id not in other_vector:
                continue
            
            if self.vector[node_id] > other_vector[node_id]:
                return False
            
            if self.vector[node_id] < other_vector[node_id]:
                at_least_one_less = True
        
        return at_least_one_less
    
    def concurrent_with(self, other_vector: Dict[str, int]) -> bool:
        """
        Check if this clock is concurrent with another
        
        Two clocks are concurrent if neither happened before the other.
        
        Args:
            other_vector: Another vector clock to compare
            
        Returns:
            True if clocks are concurrent
        """
        return not self.happened_before(other_vector) and \
               not self._other_happened_before(other_vector)
    
    def _other_happened_before(self, other_vector: Dict[str, int]) -> bool:
        """Check if other happened before this"""
        at_least_one_less = False
        
        for node_id in self.vector:
            if node_id not in other_vector:
                continue
            
            if other_vector[node_id] > self.vector[node_id]:
                at_least_one_less = True
            elif other_vector[node_id] < self.vector[node_id]:
                return False
        
        return at_least_one_less
    
    def __repr__(self):
        # Format: A[1,0,2] for node A with vector [1,0,2]
        sorted_nodes = sorted(self.vector.keys())
        values = [str(self.vector[node]) for node in sorted_nodes]
        return f"{self.node_id}[{','.join(values)}]"
    
    def __str__(self):
        return self.__repr__()


# Example usage
if __name__ == "__main__":
    print("=== Vector Clock Example ===\n")
    
    # Create clocks for three nodes
    clock_a = VectorClock("A", ["B", "C"])
    clock_b = VectorClock("B", ["A", "C"])
    clock_c = VectorClock("C", ["A", "B"])
    
    print(f"Initial: {clock_a}, {clock_b}, {clock_c}\n")
    
    # Local events
    clock_a.tick()
    print(f"After A local event: {clock_a}, {clock_b}, {clock_c}")
    
    clock_b.tick()
    print(f"After B local event: {clock_a}, {clock_b}, {clock_c}\n")
    
    # A sends to B
    msg_from_a = clock_a.send()
    print(f"A sends message: {clock_a}")
    print(f"Message vector: {msg_from_a}")
    
    clock_b.receive("A", msg_from_a)
    print(f"B receives from A: {clock_b}\n")
    
    # C has independent event (concurrent with A and B)
    clock_c.tick()
    print(f"C has local event: {clock_c}\n")
    
    # Check causality
    print("=== Causality Analysis ===")
    a_vector = clock_a.get_vector()
    b_vector = clock_b.get_vector()
    c_vector = clock_c.get_vector()
    
    print(f"A happened before B? {clock_a.happened_before(b_vector)}")
    print(f"B happened before A? {clock_b.happened_before(a_vector)}")
    print(f"A concurrent with C? {clock_a.concurrent_with(c_vector)}")
    print(f"B concurrent with C? {clock_b.concurrent_with(c_vector)}")
