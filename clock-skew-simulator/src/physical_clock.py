"""
Physical Clock with Drift Simulation

Simulates a physical clock that can drift (run faster or slower)
and have initial skew from true time.
"""

import time


class PhysicalClock:
    """
    Simulated physical clock with drift and skew
    
    Properties:
    - drift_rate: How much faster/slower the clock runs (e.g., 0.001 = 0.1%)
    - skew: Initial offset from true time (seconds)
    
    Use for simulating:
    - Clock synchronization challenges
    - NTP behavior
    - Impact of clock skew on distributed systems
    """
    
    def __init__(self, node_id: str, drift_rate: float = 0.0, skew: float = 0.0):
        """
        Initialize physical clock
        
        Args:
            node_id: Unique identifier for this node
            drift_rate: Rate of clock drift (0.001 = 0.1% faster/slower)
            skew: Initial offset from true time (seconds)
        """
        self.node_id = node_id
        self.drift_rate = drift_rate
        self.skew = skew
        
        # Record when clock was created
        self.creation_time = time.time()
    
    def read(self) -> float:
        """
        Read the clock time
        
        Returns time affected by drift and skew.
        
        Returns:
            Current time according to this clock
        """
        true_elapsed = time.time() - self.creation_time
        drifted_elapsed = true_elapsed * (1.0 + self.drift_rate)
        return self.creation_time + drifted_elapsed + self.skew
    
    def get_skew(self) -> float:
        """
        Calculate current skew from true time
        
        Returns:
            Difference between clock time and true time (seconds)
        """
        true_time = time.time()
        clock_time = self.read()
        return clock_time - true_time
    
    def synchronize(self, reference_time: float):
        """
        Synchronize clock to a reference time
        
        Adjusts skew to match reference, but drift remains.
        
        Args:
            reference_time: Time to synchronize to
        """
        current_time = self.read()
        adjustment = reference_time - current_time
        self.skew += adjustment
    
    def __repr__(self):
        return f"PhysicalClock(node={self.node_id}, drift={self.drift_rate}, skew={self.skew:.3f})"


# Example usage
if __name__ == "__main__":
    print("=== Physical Clock Drift Simulation ===\n")
    
    # Create clocks with different characteristics
    accurate_clock = PhysicalClock("accurate", drift_rate=0.0, skew=0.0)
    fast_clock = PhysicalClock("fast", drift_rate=0.01, skew=0.5)  # 1% fast, 0.5s ahead
    slow_clock = PhysicalClock("slow", drift_rate=-0.01, skew=-0.5)  # 1% slow, 0.5s behind
    
    print(f"Initial state:")
    print(f"  {accurate_clock}")
    print(f"  {fast_clock}")
    print(f"  {slow_clock}\n")
    
    # Let some time pass
    time.sleep(1.0)
    
    # Read clocks
    print("After 1 second:")
    print(f"  Accurate: {accurate_clock.read():.6f}, skew: {accurate_clock.get_skew():.6f}")
    print(f"  Fast: {fast_clock.read():.6f}, skew: {fast_clock.get_skew():.6f}")
    print(f"  Slow: {slow_clock.read():.6f}, skew: {slow_clock.get_skew():.6f}\n")
    
    # More time passes
    time.sleep(2.0)
    
    print("After 3 seconds total:")
    print(f"  Accurate skew: {accurate_clock.get_skew():.6f}")
    print(f"  Fast skew: {fast_clock.get_skew():.6f}")
    print(f"  Slow skew: {slow_clock.get_skew():.6f}\n")
    
    # Synchronize clocks
    print("Synchronizing all clocks...")
    reference_time = accurate_clock.read()
    fast_clock.synchronize(reference_time)
    slow_clock.synchronize(reference_time)
    
    print(f"After sync:")
    print(f"  Fast skew: {fast_clock.get_skew():.6f}")
    print(f"  Slow skew: {slow_clock.get_skew():.6f}\n")
    
    # Wait and show drift continues
    time.sleep(2.0)
    print("After 2 more seconds (drift continues):")
    print(f"  Fast skew: {fast_clock.get_skew():.6f}")
    print(f"  Slow skew: {slow_clock.get_skew():.6f}")
