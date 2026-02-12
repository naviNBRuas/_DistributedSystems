"""
Example: Distributed Database with Vector Clocks

Demonstrates how vector clocks are used in a replicated database
to detect concurrent updates (conflicts).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vector_clock import VectorClock
from typing import Dict, List, Any, Tuple


class ReplicatedDB:
    """
    Simulated distributed key-value store with replication
    """
    
    def __init__(self, node_id: str, peers: List[str], clock_type: str = "vector"):
        self.node_id = node_id
        self.peers = peers
        self.store: Dict[str, Any] = {}
        self.clock = VectorClock(node_id, peers)
        self.clock_type = clock_type # simplified, assuming vector for this example
        
        # Version store: {key: {node: timestamp}}
        self.versions: Dict[str, Dict[str, int]] = {}

    def put(self, key: str, value: Any):
        """
        Write a value to the database
        """
        # Update clock
        timestamp = self.clock.tick()
        
        # Store value and version
        self.store[key] = value
        self.versions[key] = timestamp
        
        print(f"[{self.node_id}] Write '{key}'='{value}' @ {timestamp}")
        
        # Simulate replication to peers (just printing here)
        self.replicate(key, value, timestamp)

    def replicate(self, key: str, value: Any, timestamp: Dict[str, int]):
        """Simulate sending update to peers"""
        print(f"[{self.node_id}] Replicating '{key}' to {self.peers}")

    def receive_replication(self, sender: str, key: str, value: Any, timestamp: Dict[str, int]):
        """
        Handle incoming replication from a peer
        """
        print(f"[{self.node_id}] Received replication from {sender}: '{key}'='{value}' @ {timestamp}")
        
        # Update local clock
        self.clock.receive(sender, timestamp)
        
        # Check for conflict
        current_version = self.versions.get(key)
        
        if current_version is None:
            # New key
            self.store[key] = value
            self.versions[key] = timestamp
            print(f"[{self.node_id}] Accepted new key '{key}'")
            return

        # Check causality
        # We need a way to check if current_version happened before incoming timestamp
        # or vice versa, or if they are concurrent.
        
        # We can use the clock instance to check relationship of the TIMESTAMP vectors
        # NOTE: VectorClock methods check 'self' vs 'other'. Here we are comparing two timestamps.
        # We need a helper or use the method if we can set state. 
        # But VectorClock doesn't support stateless comparison easily unless we use the internal logic.
        
        # Let's use the internal logic logic directly here for demonstration
        is_concurrent = False
        incoming_dominates = False
        current_dominates = False
        
        # Check if current < incoming
        if self._happens_before(current_version, timestamp):
            incoming_dominates = True
        # Check if incoming < current
        elif self._happens_before(timestamp, current_version):
            current_dominates = True
        else:
            is_concurrent = True
            
        if incoming_dominates:
            print(f"[{self.node_id}] Update is newer. Overwriting.")
            self.store[key] = value
            self.versions[key] = timestamp
        elif current_dominates:
            print(f"[{self.node_id}] Update is older (stale). Ignoring.")
        else:
            print(f"[{self.node_id}] CONFLICT DETECTED! Concurrent updates.")
            print(f"  Current: {self.store[key]} @ {current_version}")
            print(f"  Incoming: {value} @ {timestamp}")
            # Simple resolution: keep both (siblings) or LWW
            print(f"  (Resolution strategy needed)")

    def _happens_before(self, v1: Dict[str, int], v2: Dict[str, int]) -> bool:
        """Helper to compare two vector timestamps"""
        keys = set(v1.keys()) | set(v2.keys())
        le = all(v1.get(k, 0) <= v2.get(k, 0) for k in keys)
        lt = any(v1.get(k, 0) < v2.get(k, 0) for k in keys)
        return le and lt


def main():
    print("=== Distributed Database Conflict Detection ===\n")
    
    # Setup 3 replicas
    r1 = ReplicatedDB("R1", ["R2", "R3"])
    r2 = ReplicatedDB("R2", ["R1", "R3"])
    
    # R1 writes key1
    print("\n--- Step 1: R1 writes key1 ---")
    r1.put("key1", "value1")
    # Assume R2 receives it
    r2.receive_replication("R1", "key1", "value1", r1.versions["key1"])
    
    # Now concurrent updates
    print("\n--- Step 2: Concurrent updates on key1 ---")
    
    # R1 updates key1
    r1.put("key1", "value2")
    
    # R2 updates key1 independently (it hasn\'t seen R1\'s update yet)
    r2.put("key1", "value3")
    
    # R1 receives R2\'s update
    print("\n--- Step 3: R1 receives R2\'s update ---")
    r1.receive_replication("R2", "key1", "value3", r2.versions["key1"])


if __name__ == "__main__":
    main()
