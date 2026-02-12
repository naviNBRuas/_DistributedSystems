"""
NTP Simulator

Simulates Network Time Protocol (NTP) behavior for clock synchronization
in distributed systems.
"""

import random
from typing import List, Dict
from .physical_clock import PhysicalClock


class NTPSimulator:
    """
    Simulates NTP synchronization between multiple nodes.
    
    Manages a cluster of nodes with physical clocks and simulates
    the effect of NTP synchronization on reducing clock skew.
    """
    
    def __init__(self, nodes: List[str], max_clock_skew: float = 1.0, network_latency: float = 0.01):
        """
        Initialize NTP Simulator
        
        Args:
            nodes: List of node identifiers
            max_clock_skew: Maximum initial random skew (seconds)
            network_latency: simulated average network latency (seconds)
        """
        self.nodes = nodes
        self.max_clock_skew = max_clock_skew
        self.network_latency = network_latency
        
        self.clocks: Dict[str, PhysicalClock] = {}
        
        # Initialize clocks with random skew
        for node in nodes:
            # Random skew between -max and +max
            skew = random.uniform(-max_clock_skew, max_clock_skew)
            # Random small drift
            drift = random.uniform(-0.001, 0.001)
            self.clocks[node] = PhysicalClock(node, drift_rate=drift, skew=skew)
            
    def synchronize(self):
        """
        Run synchronization protocol
        
        In this simulation, we pick the first node as the 'server' (stratum 1)
        and synchronize others to it, accounting for network latency error.
        """
        if not self.nodes:
            return
            
        server_node = self.nodes[0]
        server_clock = self.clocks[server_node]
        
        # True time at server
        server_time = server_clock.read()
        
        for i in range(1, len(self.nodes)):
            client_node = self.nodes[i]
            client_clock = self.clocks[client_node]
            
            # Simulate network delay (RTT/2 + jitter)
            # Error bound in NTP is typically within tens of milliseconds
            # We simulate this by giving a slightly imperfect reference time
            latency_error = random.uniform(0, self.network_latency)
            estimated_server_time = server_time + latency_error
            
            # Sync client to this estimated time
            client_clock.synchronize(estimated_server_time)
            
    def get_max_skew(self) -> float:
        """
        Calculate maximum skew between any clock and true time
        
        Returns:
            Maximum absolute skew in seconds
        """
        max_skew = 0.0
        for clock in self.clocks.values():
            skew = abs(clock.get_skew())
            if skew > max_skew:
                max_skew = skew
        return max_skew

    def get_clock(self, node_id: str) -> PhysicalClock:
        """Get the clock for a specific node"""
        return self.clocks[node_id]
