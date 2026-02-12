"""
Simulation: Concurrent Events

High-volume concurrent event simulation to stress test
causality tracking.
"""

import sys
import os
import random
# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vector_clock import VectorClock

def main():
    print("=== Concurrent Events Stress Test ===\n")
    
    nodes = ["N1", "N2", "N3"]
    clocks = {n: VectorClock(n, [p for p in nodes if p != n]) for n in nodes}
    
    iterations = 20
    print(f"Simulating {iterations} random events...")
    
    events = [] # (node, timestamp)
    
    for i in range(iterations):
        node = random.choice(nodes)
        action = random.choice(["local", "send_recv"])
        
        if action == "local":
            ts = clocks[node].tick()
            events.append((node, ts))
            # print(f"Event {i}: {node} local -> {ts}")
            
        elif action == "send_recv":
            # Pick a receiver
            receiver = random.choice([n for n in nodes if n != node])
            
            # Send
            send_ts = clocks[node].send()
            
            # Receive
            recv_ts = clocks[receiver].receive(node, send_ts)
            events.append((receiver, recv_ts))
            # print(f"Event {i}: {node} -> {receiver} -> {recv_ts}")
            
    print("\nAnalysis:")
    print(f"Total events tracked: {len(events)}")
    
    # Check last state
    print("\nFinal Vector Clocks:")
    for n in nodes:
        print(f"{n}: {clocks[n]}")

if __name__ == "__main__":
    main()

