"""
Simulation: Clock Synchronization

Demonstrates NTP synchronization reducing clock skew over time.
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ntp_simulator import NTPSimulator
import time

def main():
    print("=== NTP Synchronization Simulation ===\n")
    
    nodes = ["node1", "node2", "node3", "node4", "node5"]
    print(f"Nodes: {nodes}")
    
    # Initialize with high skew
    sim = NTPSimulator(nodes, max_clock_skew=5.0, network_latency=0.05)
    
    # Make node1 an accurate time source (Stratum 1)
    server_clock = sim.get_clock("node1")
    server_clock.skew = 0.0
    server_clock.drift_rate = 0.0
    
    initial_skew = sim.get_max_skew()
    print(f"Initial max skew: {initial_skew:.4f} seconds")
    
    print("\nSynchronizing...")
    sim.synchronize()
    
    final_skew = sim.get_max_skew()
    print(f"Final max skew:   {final_skew:.4f} seconds")
    
    improvement = initial_skew - final_skew
    print(f"Skew reduction:   {improvement:.4f} seconds")
    
    if final_skew < 0.1:
        print("\nSUCCESS: Clocks synchronized within 100ms")
    else:
        print("\nWARNING: Synchronization precision low")

if __name__ == "__main__":
    main()

