"""
Causality Analyzer

Tools for analyzing causal relationships between events
based on their timestamps.
"""

from typing import Dict, Any, List, Optional, Tuple
from .lamport_clock import LamportClock
from .vector_clock import VectorClock
from .hybrid_clock import HLCTimestamp


class CausalityAnalyzer:
    """
    Analyzes causal relationships between recorded events.
    """
    
    def __init__(self):
        self.events: Dict[str, Any] = {}
        self.event_types: Dict[str, str] = {}
        self.timestamps: Dict[str, Any] = {}
        
    def add_event(self, event_id: str, event_type: str, timestamp: Any):
        """
        Record an event for analysis
        
        Args:
            event_id: Unique identifier for the event
            event_type: Type of event (e.g., 'send', 'receive', 'local')
            timestamp: The timestamp object (Lamport, Vector, or HLC) associated with the event
        """
        self.events[event_id] = {
            "id": event_id,
            "type": event_type,
            "timestamp": timestamp
        }
        self.timestamps[event_id] = timestamp
        self.event_types[event_id] = event_type
        
    def happens_before(self, event_a: str, event_b: str) -> bool:
        """
        Check if event A happened before event B (A -> B)
        
        Args:
            event_a: ID of first event
            event_b: ID of second event
            
        Returns:
            True if A -> B
        """
        ts_a = self.timestamps.get(event_a)
        ts_b = self.timestamps.get(event_b)
        
        if ts_a is None or ts_b is None:
            raise ValueError("Event ID not found")
            
        # Dispatch based on timestamp type
        if isinstance(ts_a, int) and isinstance(ts_b, int):
            # Lamport timestamps (int)
            return ts_a < ts_b
            
        elif isinstance(ts_a, dict) and isinstance(ts_b, dict):
            # Vector clocks
            return self._vector_happens_before(ts_a, ts_b)
            
        elif isinstance(ts_a, HLCTimestamp) and isinstance(ts_b, HLCTimestamp):
            # HLC
            return ts_a < ts_b
            
        else:
            # Mismatched or unknown types
            return False

    def concurrent(self, event_a: str, event_b: str) -> bool:
        """
        Check if event A and B are concurrent (A || B)
        
        Args:
            event_a: ID of first event
            event_b: ID of second event
            
        Returns:
            True if concurrent (neither happens before the other)
        """
        return not self.happens_before(event_a, event_b) and \
               not self.happens_before(event_b, event_a)

    def _vector_happens_before(self, vc1: Dict[str, int], vc2: Dict[str, int]) -> bool:
        """Check vector clock happens-before relationship"""
        keys = set(vc1.keys()) | set(vc2.keys())
        
        le = all(vc1.get(k, 0) <= vc2.get(k, 0) for k in keys)
        lt = any(vc1.get(k, 0) < vc2.get(k, 0) for k in keys)
        
        return le and lt