"""
Latency Injector

Simulates network latency and delays for testing.
"""

import time
import random
from typing import Dict, Callable, Optional


class LatencyInjector:
    """
    Network latency injection for testing
    
    Simulates various latency patterns:
    - Fixed latency
    - Variable latency with jitter
    - Latency based on message size
    - Network congestion simulation
    """
    
    def __init__(self):
        """Initialize latency injector"""
        # Latency configuration: (source, target) -> latency_config
        self.latencies: Dict[tuple, dict] = {}
    
    def add_latency(
        self,
        source: str,
        target: str,
        latency_ms: Optional[float] = None,
        jitter_ms: float = 0,
        latency_fn: Optional[Callable] = None
    ):
        """
        Add latency between two nodes
        
        Args:
            source: Source node ID
            target: Target node ID
            latency_ms: Fixed latency in milliseconds
            jitter_ms: Random jitter (±jitter_ms)
            latency_fn: Function(message_size) -> latency_ms
        """
        config = {
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "latency_fn": latency_fn
        }
        
        self.latencies[(source, target)] = config
        print(f"[LatencyInjector] Added latency {source} -> {target}: {latency_ms}ms (jitter: ±{jitter_ms}ms)")
    
    def remove_latency(self, source: str, target: str):
        """Remove latency between two nodes"""
        if (source, target) in self.latencies:
            del self.latencies[(source, target)]
            print(f"[LatencyInjector] Removed latency {source} -> {target}")
    
    def get_latency(self, source: str, target: str, message_size: int = 0) -> float:
        """
        Get latency for a message
        
        Args:
            source: Source node
            target: Target node
            message_size: Size of message in bytes
            
        Returns:
            Latency in seconds
        """
        config = self.latencies.get((source, target))
        if not config:
            return 0.0
        
        # Calculate base latency
        if config["latency_fn"]:
            latency_ms = config["latency_fn"](message_size)
        else:
            latency_ms = config["latency_ms"] or 0
        
        # Add jitter
        jitter = random.uniform(-config["jitter_ms"], config["jitter_ms"])
        total_latency_ms = max(0, latency_ms + jitter)
        
        return total_latency_ms / 1000.0  # Convert to seconds
    
    def delay_message(self, source: str, target: str, message_size: int = 0):
        """
        Apply latency delay (blocking call)
        
        Args:
            source: Source node
            target: Target node
            message_size: Message size in bytes
        """
        latency = self.get_latency(source, target, message_size)
        if latency > 0:
            time.sleep(latency)
    
    def simulate_congestion(
        self,
        nodes: list[str],
        base_latency_ms: float,
        peak_latency_ms: float,
        duration: float
    ):
        """
        Simulate network congestion with increasing latency
        
        Args:
            nodes: Nodes to affect
            base_latency_ms: Starting latency
            peak_latency_ms: Peak latency
            duration: Congestion duration in seconds
        """
        print(f"[LatencyInjector] Simulating congestion for {duration}s")
        print(f"  Latency ramp: {base_latency_ms}ms -> {peak_latency_ms}ms")
        
        # Add latencies between all node pairs
        for source in nodes:
            for target in nodes:
                if source != target:
                    # Use function that ramps up over time
                    def latency_fn(msg_size, start_time=time.time()):
                        elapsed = time.time() - start_time
                        if elapsed >= duration:
                            return peak_latency_ms
                        
                        # Linear ramp
                        progress = elapsed / duration
                        return base_latency_ms + (peak_latency_ms - base_latency_ms) * progress
                    
                    self.add_latency(
                        source=source,
                        target=target,
                        latency_fn=latency_fn
                    )
    
    def clear_all(self):
        """Remove all latency configurations"""
        self.latencies.clear()
        print("[LatencyInjector] Cleared all latencies")


# Example usage
if __name__ == "__main__":
    print("=== Latency Injector Example ===\n")
    
    injector = LatencyInjector()
    
    # Add fixed latency
    injector.add_latency("node1", "node2", latency_ms=100, jitter_ms=10)
    
    # Test latency
    print("--- Testing Latency ---")
    for i in range(5):
        latency = injector.get_latency("node1", "node2")
        print(f"Latency {i+1}: {latency*1000:.1f}ms")
    
    # Test delay
    print("\n--- Testing Delay ---")
    start = time.time()
    injector.delay_message("node1", "node2")
    elapsed = time.time() - start
    print(f"Delayed for: {elapsed*1000:.1f}ms")
    
    # Variable latency based on message size
    print("\n--- Variable Latency ---")
    injector.add_latency(
        "node2", "node3",
        latency_fn=lambda size: 10 + size / 1000  # 10ms + 1ms per KB
    )
    
    for size in [0, 1000, 5000, 10000]:
        latency = injector.get_latency("node2", "node3", size)
        print(f"Message size {size} bytes: {latency*1000:.1f}ms")
