"""
Hybrid Logical Clock (HLC) Implementation

Combines physical time with logical counters to provide:
- Causality tracking (like vector clocks)
- Timestamps close to physical time
- Bounded logical component

Reference: "Logical Physical Clocks and Consistent Snapshots 
in Globally Distributed Databases" by Kulkarni et al. (2014)
"""

import time
from dataclasses import dataclass
from typing import Tuple


@dataclass
class HLCTimestamp:
    """
    Hybrid Logical Clock timestamp
    
    Consists of:
    - physical: Physical time component (wall clock)
    - logical: Logical counter (for events at same physical time)
    """
    physical: int  # Typically milliseconds since epoch
    logical: int   # Logical counter
    
    def __lt__(self, other):
        """Compare timestamps: first by physical, then logical"""
        if not isinstance(other, HLCTimestamp):
            return NotImplemented
        if self.physical != other.physical:
            return self.physical < other.physical
        return self.logical < other.logical
    
    def __eq__(self, other):
        if not isinstance(other, HLCTimestamp):
            return NotImplemented
        return self.physical == other.physical and self.logical == other.logical
    
    def __repr__(self):
        return f"HLC({self.physical}, {self.logical})"


class HybridLogicalClock:
    """
    Hybrid Logical Clock implementation
    
    Properties:
    - Timestamps are close to physical time
    - Provides causality like Lamport clocks
    - Bounded logical component (resets when physical time advances)
    - More compact than vector clocks
    
    Use cases:
    - Distributed databases (CockroachDB, MongoDB)
    - Consistent snapshots
    - TTL and expiration
    """
    
    def __init__(self, node_id: str):
        """
        Initialize hybrid logical clock
        
        Args:
            node_id: Unique identifier for this node
        """
        self.node_id = node_id
        self.physical = 0
        self.logical = 0
    
    def _physical_time(self) -> int:
        """Get current physical time (milliseconds since epoch)"""
        return int(time.time() * 1000)
    
    def now(self) -> HLCTimestamp:
        """
        Get current HLC timestamp
        
        Returns:
            Current timestamp
        """
        pt = self._physical_time()
        
        if pt > self.physical:
            # Physical time advanced, reset logical
            self.physical = pt
            self.logical = 0
        else:
            # Physical time same or went backwards, increment logical
            self.logical += 1
        
        return HLCTimestamp(self.physical, self.logical)
    
    def tick(self) -> HLCTimestamp:
        """
        Increment clock for a local event
        
        Returns:
            Timestamp for the event
        """
        return self.now()
    
    def send(self) -> HLCTimestamp:
        """
        Prepare to send a message
        
        Returns:
            Timestamp to include with message
        """
        return self.now()
    
    def receive(self, message_timestamp: HLCTimestamp) -> HLCTimestamp:
        """
        Update clock upon receiving a message
        
        Args:
            message_timestamp: Timestamp from received message
            
        Returns:
            New local timestamp
        """
        pt = self._physical_time()
        
        # Update physical to max of (local, message, physical_time)
        max_physical = max(self.physical, message_timestamp.physical, pt)
        
        if max_physical == self.physical and max_physical == message_timestamp.physical:
            # Same physical time, increment logical
            self.logical = max(self.logical, message_timestamp.logical) + 1
        elif max_physical == self.physical:
            # Our physical time is max
            self.logical += 1
        elif max_physical == message_timestamp.physical:
            # Message physical time is max
            self.physical = message_timestamp.physical
            self.logical = message_timestamp.logical + 1
        else:
            # Physical time advanced
            self.physical = pt
            self.logical = 0
        
        return HLCTimestamp(self.physical, self.logical)
    
    def get_timestamp(self) -> HLCTimestamp:
        """Get current timestamp without advancing clock"""
        return HLCTimestamp(self.physical, self.logical)
    
    def __repr__(self):
        return f"HLC(node={self.node_id}, physical={self.physical}, logical={self.logical})"


# Example usage
if __name__ == "__main__":
    print("=== Hybrid Logical Clock Example ===\n")
    
    # Create clocks for two nodes
    clock_a = HybridLogicalClock("A")
    clock_b = HybridLogicalClock("B")
    
    # Local events
    ts_a1 = clock_a.tick()
    print(f"A event 1: {ts_a1}")
    
    # Small delay to advance physical time
    time.sleep(0.001)
    
    ts_a2 = clock_a.tick()
    print(f"A event 2: {ts_a2}")
    
    # Multiple events at same physical time
    ts_a3 = clock_a.tick()
    ts_a4 = clock_a.tick()
    print(f"A event 3: {ts_a3}")
    print(f"A event 4: {ts_a4}")
    print("(Note: physical time same, logical increments)\n")
    
    # Send message from A to B
    msg_ts = clock_a.send()
    print(f"A sends message: {msg_ts}")
    
    # B receives message
    ts_b = clock_b.receive(msg_ts)
    print(f"B receives: {ts_b}")
    
    # Demonstrate causality
    print("\n=== Causality ===")
    print(f"A's event 1 < B's receive? {ts_a1 < ts_b}")
    print(f"A's send < B's receive? {msg_ts < ts_b}")
    
    # Demonstrate timestamps close to physical time
    print("\n=== Physical Time Closeness ===")
    actual_time = int(time.time() * 1000)
    print(f"Actual physical time: {actual_time}")
    print(f"HLC physical component: {clock_b.physical}")
    print(f"Difference: {actual_time - clock_b.physical} ms")
