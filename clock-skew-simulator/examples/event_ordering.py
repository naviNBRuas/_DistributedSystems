"""
Example: Event Ordering using Lamport Clocks

Demonstrates how Lamport clocks can be used to order
events across distributed nodes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lamport_clock import LamportClock, LamportTimestamp
from typing import List, Tuple


class DistributedLogger:
    """
    Distributed logging system with total event ordering
    
    Uses Lamport clocks to order log events across multiple nodes.
    """
    
    def __init__(self, node_ids: List[str]):
        """
        Initialize distributed logger
        
        Args:
            node_ids: List of node IDs in the system
        """
        # Create a clock for each node
        self.clocks = {node_id: LamportClock(node_id) for node_id in node_ids}
        
        # Store log events
        self.events: List[Tuple[LamportTimestamp, str, str]] = []
    
    def log(self, node_id: str, message: str):
        """
        Log an event on a specific node
        
        Args:
            node_id: Node that generated the event
            message: Log message
        """
        clock = self.clocks[node_id]
        timestamp = clock.tick()
        
        # Create timestamped log entry
        ts = LamportTimestamp(timestamp, node_id)
        self.events.append((ts, node_id, message))
        
        print(f"[{node_id}@{timestamp}] {message}")
    
    def send_message(self, from_node: str, to_node: str, message: str):
        """
        Simulate sending a message between nodes
        
        Args:
            from_node: Sender node ID
            to_node: Receiver node ID
            message: Message content
        """
        # Sender increments clock
        from_clock = self.clocks[from_node]
        send_ts = from_clock.send()
        
        print(f"[{from_node}@{send_ts}] Sending to {to_node}: {message}")
        
        # Receiver updates clock
        to_clock = self.clocks[to_node]
        receive_ts = to_clock.receive(send_ts)
        
        print(f"[{to_node}@{receive_ts}] Received from {from_node}: {message}")
        
        # Log both events
        self.events.append((LamportTimestamp(send_ts, from_node), from_node, f"SEND -> {to_node}: {message}"))
        self.events.append((LamportTimestamp(receive_ts, to_node), to_node, f"RECV <- {from_node}: {message}"))
    
    def get_ordered_logs(self) -> List[Tuple[LamportTimestamp, str, str]]:
        """
        Get logs ordered by Lamport timestamps
        
        Returns:
            Sorted list of (timestamp, node_id, message) tuples
        """
        return sorted(self.events, key=lambda x: x[0])
    
    def print_ordered_logs(self):
        """Print logs in total order"""
        print("\n=== ORDERED EVENT LOG ===")
        for ts, node_id, message in self.get_ordered_logs():
            print(f"[{node_id}@{ts.time}] {message}")


def main():
    """Example usage of distributed logger"""
    
    print("=== Distributed Event Ordering Example ===\n")
    
    # Create logger for 3 nodes
    logger = DistributedLogger(["A", "B", "C"])
    
    # Simulate distributed events
    print("--- Generating Events ---\n")
    
    logger.log("A", "User login")
    logger.log("B", "Database query")
    logger.send_message("A", "B", "Request user data")
    logger.log("B", "Process request")
    logger.send_message("B", "A", "User data response")
    logger.log("C", "Background job started")
    logger.log("A", "Display user profile")
    logger.send_message("C", "A", "Job complete")
    
    # Print events in total order
    logger.print_ordered_logs()
    
    # Demonstrate ordering properties
    print("\n=== Ordering Properties ===")
    ordered = logger.get_ordered_logs()
    print(f"Total events: {len(ordered)}")
    print(f"First event: {ordered[0]}")
    print(f"Last event: {ordered[-1]}")


if __name__ == "__main__":
    main()
