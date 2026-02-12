"""
Simulation: Network Partition

Simulates a network partition where two groups of nodes
cannot communicate, leading to causality divergence.
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vector_clock import VectorClock
from src.causality import CausalityAnalyzer

def main():
    print("=== Network Partition Simulation ===\n")
    
    nodes = ["A", "B", "C", "D"]
    partition1 = ["A", "B"]
    partition2 = ["C", "D"]
    
    print(f"Partition 1: {partition1}")
    print(f"Partition 2: {partition2}")
    print("(Nodes can only communicate within their partition)\n")
    
    # Initialize clocks
    clocks = {n: VectorClock(n, [p for p in nodes if p != n]) for n in nodes}
    analyzer = CausalityAnalyzer()
    
    # Events in Partition 1
    print("--- Partition 1 Events ---")
    # A does something
    ts_a = clocks["A"].tick()
    analyzer.add_event("A1", "local", ts_a)
    print(f"A event: {ts_a}")
    
    # A sends to B
    ts_msg = clocks["A"].send()
    analyzer.add_event("A_send", "send", ts_msg)
    
    # B receives
    ts_b = clocks["B"].receive("A", ts_msg)
    analyzer.add_event("B_recv", "receive", ts_b)
    print(f"B received from A: {ts_b}")
    
    # Events in Partition 2 (Concurrent with P1)
    print("\n--- Partition 2 Events ---")
    # C does something
    ts_c = clocks["C"].tick()
    analyzer.add_event("C1", "local", ts_c)
    print(f"C event: {ts_c}")
    
    # C sends to D
    ts_msg_c = clocks["C"].send()
    # D receives
    ts_d = clocks["D"].receive("C", ts_msg_c)
    analyzer.add_event("D_recv", "receive", ts_d)
    print(f"D received from C: {ts_d}")
    
    # Partition heals?
    # Suppose A tries to verify causality with D
    print("\n--- Partition Analysis ---")
    
    if analyzer.concurrent("B_recv", "D_recv"):
        print("Events 'B_recv' and 'D_recv' are CONCURRENT.")
        print("This confirms the partitions evolved independently.")
    else:
        print("Unexpected causality relationship found.")

if __name__ == "__main__":
    main()
