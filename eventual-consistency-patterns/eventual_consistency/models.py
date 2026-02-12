import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union
from enum import Enum

class Ordering(Enum):
    LT = -1
    EQ = 0
    GT = 1
    CONCURRENT = 2

@dataclass
class VectorClock:
    """
    A Vector Clock implementation for causal ordering.
    """
    clock: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str):
        """Increments the counter for the given node_id."""
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def merge(self, other: 'VectorClock'):
        """Merges this clock with another, taking the max of each component."""
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            self.clock[node] = max(self.clock.get(node, 0), other.clock.get(node, 0))

    def compare(self, other: 'VectorClock') -> Ordering:
        """
        Compares this vector clock with another.
        Returns Ordering.LT if self < other
        Returns Ordering.GT if self > other
        Returns Ordering.EQ if self == other
        Returns Ordering.CONCURRENT if they are concurrent
        """
        keys = set(self.clock.keys()) | set(other.clock.keys())
        has_lt = False
        has_gt = False

        for k in keys:
            val_self = self.clock.get(k, 0)
            val_other = other.clock.get(k, 0)
            if val_self < val_other:
                has_lt = True
            elif val_self > val_other:
                has_gt = True

        if has_lt and has_gt:
            return Ordering.CONCURRENT
        if has_lt:
            return Ordering.LT
        if has_gt:
            return Ordering.GT
        return Ordering.EQ

    def copy(self) -> 'VectorClock':
        return VectorClock(self.clock.copy())

@dataclass
class VersionedValue:
    """
    Holds a value with associated metadata for consistency checks.
    """
    value: Any
    timestamp: float = field(default_factory=time.time)
    vector_clock: VectorClock = field(default_factory=VectorClock)
    
    def __repr__(self):
        return f"VersionedValue(value={self.value}, ts={self.timestamp}, vc={self.clock})"
