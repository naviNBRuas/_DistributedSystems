import time
import math
import statistics
from typing import Dict, List, Deque
from collections import deque
import threading

class PhiAccrualFailureDetector:
    """
    Implementation of the Phi Accrual Failure Detector.
    
    Calculates a suspicion level (phi) for a node based on the history of 
    heartbeat arrival times.
    """
    
    def __init__(self, threshold: float = 8.0, window_size: int = 1000, min_std_dev: float = 0.1):
        self.threshold = threshold
        self.window_size = window_size
        self.min_std_dev = min_std_dev
        self.arrival_intervals: Dict[str, Deque[float]] = {}
        self.last_arrival_times: Dict[str, float] = {}
        self.lock = threading.RLock()

    def report_heartbeat(self, node_id: str):
        """Record a heartbeat from a node."""
        now = time.time()
        with self.lock:
            if node_id in self.last_arrival_times:
                interval = now - self.last_arrival_times[node_id]
                if node_id not in self.arrival_intervals:
                    self.arrival_intervals[node_id] = deque(maxlen=self.window_size)
                self.arrival_intervals[node_id].append(interval)
            
            self.last_arrival_times[node_id] = now

    def is_available(self, node_id: str) -> bool:
        """Check if a node is available (phi < threshold)."""
        return self.get_phi(node_id) < self.threshold

    def get_phi(self, node_id: str) -> float:
        """Calculate the phi value for a node."""
        with self.lock:
            if node_id not in self.last_arrival_times:
                return 0.0 # Treat unknown as alive initially or handle separately
            
            if node_id not in self.arrival_intervals or len(self.arrival_intervals[node_id]) < 2:
                return 0.0

            time_since_last = time.time() - self.last_arrival_times[node_id]
            intervals = self.arrival_intervals[node_id]
            mean = statistics.mean(intervals)
            std_dev = max(statistics.stdev(intervals), self.min_std_dev)
            
            return self._calculate_phi(time_since_last, mean, std_dev)

    def _calculate_phi(self, time_since_last: float, mean: float, std_dev: float) -> float:
        """
        Calculate phi based on normal distribution assumption.
        phi = -log10(P_later(t))
        P_later(t) = probability that the heartbeat will arrive later than t
        """
        y = (time_since_last - mean) / std_dev
        p = self._cdf(y)
        p_later = 1.0 - p
        
        # Avoid log(0)
        if p_later < 1e-12:
            p_later = 1e-12
            
        return -math.log10(p_later)

    def _cdf(self, x: float) -> float:
        """Cumulative distribution function for normal distribution."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def remove_node(self, node_id: str):
        """Remove a node from tracking."""
        with self.lock:
            self.arrival_intervals.pop(node_id, None)
            self.last_arrival_times.pop(node_id, None)
