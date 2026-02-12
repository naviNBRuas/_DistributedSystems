"""
Example: Clock Drift Visualization

Visualizes how physical clocks drift over time compared to true time.
"""

import sys
import os
import time
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from physical_clock import PhysicalClock
from visualizer import ClockDriftVisualizer


def main():
    print("=== Clock Drift Demo ===\n")
    print("Simulating clocks running for 10 seconds...")
    
    # Create clocks
    # Node 1: Accurate
    c1 = PhysicalClock("accurate", drift_rate=0.0)
    
    # Node 2: Fast (1% fast)
    c2 = PhysicalClock("fast", drift_rate=0.01)
    
    # Node 3: Slow (1% slow)
    c3 = PhysicalClock("slow", drift_rate=-0.01)
    
    # Node 4: Wobbly (random drift)
    c4 = PhysicalClock("skewed", drift_rate=0.005, skew=0.5)

    viz = ClockDriftVisualizer()
    
    # Simulation loop
    start_time = time.time()
    duration = 2.0  # Run for 2 seconds real time (simulating fast)
    
    # We'll pretend time moves faster for the simulation
    # We'll define a 'true_time' that advances
    
    current_sim_time = 0.0
    steps = 20
    
    for i in range(steps):
        # Record readings
        viz.add_reading(c1.node_id, current_sim_time, c1.read())
        viz.add_reading(c2.node_id, current_sim_time, c2.read())
        viz.add_reading(c3.node_id, current_sim_time, c3.read())
        viz.add_reading(c4.node_id, current_sim_time, c4.read())
        
        # Advance time
        time.sleep(0.05)
        current_sim_time += 0.5 # Simulate 0.5s passing every 0.05s
        
        # Hack: manually advance clocks to match simulated time passing
        # Since PhysicalClock relies on system time.time(), we can't easily speed it up
        # unless we mock time or just wait.
        # To make a nice graph without waiting 10s, we'll just manually inject readings
        # based on the drift formula: true_time * (1 + drift) + skew
        
        # Re-calculating for visualization purpose to match 'current_sim_time'
        # c1
        viz.add_reading("accurate", current_sim_time, current_sim_time)
        
        # c2 (fast)
        viz.add_reading("fast", current_sim_time, current_sim_time * 1.01)
        
        # c3 (slow)
        viz.add_reading("slow", current_sim_time, current_sim_time * 0.99)
        
        # c4 (skewed)
        viz.add_reading("skewed", current_sim_time, current_sim_time * 1.005 + 0.5)

    print("Simulation complete.")
    
    output_file = "drift_demo.png"
    viz.plot(output_file)
    print(f"Visualization saved to {output_file} (if matplotlib is installed)")

if __name__ == "__main__":
    main()
