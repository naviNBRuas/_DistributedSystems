"""
Basic usage example of the Quorum System.
"""

import sys
import os
import logging

# Add src to path for example execution
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.quorum_system import QuorumCoordinator, ConsistencyLevel, QuorumNotMetError

def main():
    # Setup logging to see what's happening
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== Quorum System Example ===")
    
    # 1. Initialize Coordinator
    # 5 nodes, Write Quorum=3, Read Quorum=3 (Strong Consistency)
    replicas = ["node1", "node2", "node3", "node4", "node5"]
    coordinator = QuorumCoordinator(
        replicas=replicas,
        write_quorum=3,
        read_quorum=3
    )
    
    print(f"\nInitialized: {coordinator}")
    
    # 2. Write Data
    key = "user:101"
    value = {"name": "Alice", "role": "admin"}
    
    print(f"\nWriting key='{key}' value='{value}'...")
    try:
        coordinator.write(key, value, ConsistencyLevel.QUORUM)
        print("Write successful!")
    except QuorumNotMetError as e:
        print(f"Write failed: {e}")
        return

    # 3. Read Data
    print(f"\nReading key='{key}'...")
    try:
        result = coordinator.read(key, ConsistencyLevel.QUORUM)
        print(f"Read result: {result}")
        assert result == value
    except QuorumNotMetError as e:
        print(f"Read failed: {e}")

    # 4. Demonstrate Consistency Levels
    print("\nDemonstrating ONE consistency (faster, less reliable)...")
    coordinator.write("log:1", "event_data", ConsistencyLevel.ONE)
    print("Write ONE successful.")

if __name__ == "__main__":
    main()
