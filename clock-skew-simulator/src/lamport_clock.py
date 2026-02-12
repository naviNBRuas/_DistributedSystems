"""
Lamport Logical Clock Implementation

Provides logical timestamps for establishing total ordering
of events in a distributed system.

Reference: "Time, Clocks, and the Ordering of Events in a 
Distributed System" by Leslie Lamport (1978)
"""


class LamportClock:
    """
    Lamport logical clock implementation
    
    Properties:
    - Monotonically increasing counter
    - If event A happened before event B, then timestamp(A) < timestamp(B)
    - Simple and space-efficient (single integer)
    
    Limitations:
    - Cannot detect concurrent events
    - timestamp(A) < timestamp(B) does NOT imply A happened before B
    """
    
    def __init__(self, node_id: str, initial_time: int = 0):
        """
        Initialize Lamport clock
        
        Args:
            node_id: Unique identifier for this node
            initial_time: Starting timestamp (default: 0)
        """
        self.node_id = node_id
        self.time = initial_time
    
    def tick(self) -> int:
        """
        Increment clock for a local event
        
        Returns:
            Current timestamp after increment
        """
        self.time += 1
        return self.time
    
    def send(self) -> int:
        """
        Prepare to send a message
        
        Increments clock and returns timestamp to attach to message.
        
        Returns:
            Timestamp to include with message
        """
        self.time += 1
        return self.time
    
    def receive(self, message_timestamp: int) -> int:
        """
        Update clock upon receiving a message
        
        Updates clock to max(local_time, message_time) + 1
        
        Args:
            message_timestamp: Timestamp from received message
            
        Returns:
            New local timestamp
        """
        self.time = max(self.time, message_timestamp) + 1
        return self.time
    
    def get_time(self) -> int:
        """Get current timestamp without incrementing"""
        return self.time
    
    def __repr__(self):
        return f"LamportClock(node={self.node_id}, time={self.time})"
    
    def __lt__(self, other):
        """Compare timestamps (for sorting)"""
        if not isinstance(other, LamportClock):
            return NotImplemented
        return self.time < other.time
    
    def __eq__(self, other):
        """Check timestamp equality"""
        if not isinstance(other, LamportClock):
            return NotImplemented
        return self.time == other.time


class LamportTimestamp:
    """
    A Lamport timestamp with node ID for tie-breaking
    
    Provides total ordering: first by time, then by node ID
    """
    
    def __init__(self, time: int, node_id: str):
        self.time = time
        self.node_id = node_id
    
    def __lt__(self, other):
        """Total ordering: first by time, then by node ID"""
        if not isinstance(other, LamportTimestamp):
            return NotImplemented
        if self.time != other.time:
            return self.time < other.time
        return self.node_id < other.node_id
    
    def __eq__(self, other):
        if not isinstance(other, LamportTimestamp):
            return NotImplemented
        return self.time == other.time and self.node_id == other.node_id
    
    def __repr__(self):
        return f"LamportTimestamp(time={self.time}, node={self.node_id})"


# Example usage
if __name__ == "__main__":
    print("=== Lamport Clock Example ===\n")
    
    # Create clocks for two nodes
    clock_a = LamportClock("A")
    clock_b = LamportClock("B")
    
    print(f"Initial: {clock_a}, {clock_b}")
    
    # Local event on A
    clock_a.tick()
    print(f"After A local event: {clock_a}, {clock_b}")
    
    # A sends message to B
    msg_timestamp = clock_a.send()
    print(f"After A sends message: {clock_a}, {clock_b}")
    print(f"Message timestamp: {msg_timestamp}")
    
    # B receives message
    clock_b.receive(msg_timestamp)
    print(f"After B receives: {clock_a}, {clock_b}")
    
    # B has local event
    clock_b.tick()
    print(f"After B local event: {clock_a}, {clock_b}")
    
    # Demonstrate total ordering
    print("\n=== Total Ordering ===")
    events = [
        LamportTimestamp(3, "A"),
        LamportTimestamp(1, "B"),
        LamportTimestamp(3, "B"),
        LamportTimestamp(2, "A"),
    ]
    
    print("Unordered events:", events)
    print("Ordered events:", sorted(events))
