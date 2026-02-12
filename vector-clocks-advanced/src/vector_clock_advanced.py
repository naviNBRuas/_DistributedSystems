"""
Dotted Version Vectors (DVV) and Interval Tree Clocks (ITC)

Advanced causality tracking with precise version information
for distributed systems.
"""

from typing import Dict, Set, Tuple, Optional, Any, List, Union
from dataclasses import dataclass, field
import logging
import copy

logger = logging.getLogger(__name__)

@dataclass
class DottedVersionVector:
    """
    Dotted Version Vector (DVV)
    
    Tracks causality in distributed systems with support for:
    - Vector clocks (contiguous causal history)
    - Dots (discontinuous/concurrent events)
    - Causality checks (happens-before)
    """
    
    actor: str
    clock: Dict[str, int] = field(default_factory=dict)
    dots: Set[Tuple[str, int]] = field(default_factory=set)
    
    def __init__(self, actor: str):
        if not actor:
            raise ValueError("Actor ID cannot be empty")
        self.actor = actor
        self.clock = {actor: 0}
        self.dots = set()
    
    @property
    def size(self) -> int:
        """Returns the number of actors tracked in the vector clock."""
        return len(self.clock)

    def increment(self, timestamp: Optional[int] = None) -> int:
        """
        Increment logical clock for this actor.
        
        Args:
            timestamp: Optional specific timestamp to set (must be > current).
                       If None, increments current max by 1.
        
        Returns:
            The new timestamp.
        """
        current = self.clock.get(self.actor, 0)
        if timestamp is not None:
            if timestamp <= current:
                raise ValueError(f"New timestamp {timestamp} must be greater than current {current}")
            new_ts = timestamp
        else:
            new_ts = current + 1
            
        self.dots.add((self.actor, new_ts))
        
        # Only advance the contiguous clock if we are extending the sequence exactly
        if new_ts == current + 1:
            self.clock[self.actor] = new_ts
            # We might have bridged a gap to future dots
            self._compact_dots()
            
        return new_ts
    
    def event(self, other: Optional['DottedVersionVector'] = None) -> int:
        """
        Record a causal event, potentially merging with another DVV.
        """
        if other:
            self.merge(other)
        return self.increment()
    
    def merge(self, other: 'DottedVersionVector') -> 'DottedVersionVector':
        """
        Merge two DVVs in place.
        
        Syncs knowledge from 'other' into 'self'.
        """
        if not isinstance(other, DottedVersionVector):
            raise TypeError("Can only merge with DottedVersionVector")

        # 1. Merge dots
        self.dots.update(other.dots)
        
        # 2. Merge clocks (take max)
        for actor, ts in other.clock.items():
            self.clock[actor] = max(self.clock.get(actor, 0), ts)
            
        # 3. Compact dots (remove dots covered by clock)
        self._compact_dots()
        return self

    def _compact_dots(self):
        """Remove dots that are already covered by the contiguous clock vectors."""
        # A dot (actor, ts) is redundant if ts <= clock[actor]
        # However, we must ensure we don't lose information.
        # Standard DVV: clock[a]=N implies (a,1)..(a,N) are known.
        # So we keep dots that are > clock[a].
        
        # Also, if we have dots (a, N+1), (a, N+2)... contiguous after clock,
        # we can advance the clock and remove those dots.
        
        # 1. Identify all unique actors involved in dots
        dot_actors = {a for a, _ in self.dots}
        
        for actor in dot_actors:
            current_max = self.clock.get(actor, 0)
            
            # Get all dots for this actor
            actor_dots = [ts for a, ts in self.dots if a == actor]
            if not actor_dots:
                continue
                
            actor_dots.sort()
            
            # Try to extend the contiguous range
            # Example: clock=5, dots=[6, 7, 9]. New clock=7, dots=[9].
            
            # Optimization: only check dots > current_max
            # (dots <= current_max are redundant anyway)
            
            extended_max = current_max
            for ts in actor_dots:
                if ts == extended_max + 1:
                    extended_max = ts
                elif ts <= current_max:
                    # Already covered
                    pass
                else:
                    # Gap found (ts > extended_max + 1)
                    # Cannot extend further
                    pass
            
            if extended_max > current_max:
                self.clock[actor] = extended_max
        
        # Final cleanup: remove all dots <= clock[actor]
        # Because we potentially updated clock[actor] above.
        self.dots = {(a, ts) for a, ts in self.dots if ts > self.clock.get(a, 0)}

    def is_subset(self, other: 'DottedVersionVector') -> bool:
        """
        Returns True if self <= other.
        i.e., 'other' knows everything 'self' knows.
        """
        # 1. Check strict vector clock coverage
        # For every actor in self.clock, 'other' must cover the range 1..self.clock[actor]
        for actor, ts in self.clock.items():
            other_clock_ts = other.clock.get(actor, 0)
            if ts > other_clock_ts:
                # 'other' clock is lagging. It MUST have dots to cover the gap.
                # Gap: [other_clock_ts + 1, ts]
                for missing_ts in range(other_clock_ts + 1, ts + 1):
                    if (actor, missing_ts) not in other.dots:
                        return False
        
        # 2. Check independent dots coverage
        for actor, ts in self.dots:
            other_clock_ts = other.clock.get(actor, 0)
            if ts > other_clock_ts:
                # If dot is beyond other's clock, it MUST be in other's dots
                if (actor, ts) not in other.dots:
                    return False
                    
        return True

    def happens_before(self, other: 'DottedVersionVector') -> bool:
        """
        Check if self -> other (strict causal precedence).
        True if self <= other AND self != other.
        """
        if not isinstance(other, DottedVersionVector):
            raise TypeError("Comparison requires DottedVersionVector")
            
        is_leq = self.is_subset(other)
        if not is_leq:
            return False
            
        # Check inequality: either other is not subset of self (meaning other has more info)
        # or structures are different.
        # Since self <= other, strict inequality means other is NOT <= self.
        return not other.is_subset(self)

    def concurrent(self, other: 'DottedVersionVector') -> bool:
        return not self.is_subset(other) and not other.is_subset(self)
        
    def __le__(self, other):
        return self.is_subset(other)
        
    def __lt__(self, other):
        return self.happens_before(other)
        
    def __eq__(self, other):
        return self.is_subset(other) and other.is_subset(self)

    def to_dict(self) -> dict:
        return {
            "actor": self.actor,
            "clock": self.clock.copy(),
            "dots": sorted(list(self.dots)) # Sort for deterministic output
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DottedVersionVector':
        dvv = cls(data["actor"])
        dvv.clock = data.get("clock", {}).copy()
        dots_list = data.get("dots", [])
        dvv.dots = set(tuple(d) for d in dots_list)
        return dvv
        
    def copy(self) -> 'DottedVersionVector':
        new_dvv = DottedVersionVector(self.actor)
        new_dvv.clock = self.clock.copy()
        new_dvv.dots = self.dots.copy()
        return new_dvv

    def __repr__(self):
        return f"DVV({self.actor}, clock={self.clock}, dots={len(self.dots)})"


@dataclass
class IntervalTreeClock:
    """
    Interval Tree Clock (ITC) wrapper.
    
    Note: This implementation tracks hierarchical causality via counters,
    simplifying the theoretical bit-splitting ITC for general usage.
    """
    
    id: str
    counter: int = 0
    children: Dict[str, 'IntervalTreeClock'] = field(default_factory=dict)
    
    def __init__(self, id: str = "root"):
        self.id = id
        self.counter = 0
        self.children = {}
    
    def fork(self, child_id: str) -> 'IntervalTreeClock':
        """
        Creates a child clock. The child inherits the current counter state.
        """
        if child_id in self.children:
            raise ValueError(f"Child {child_id} already exists")
            
        child = IntervalTreeClock(child_id)
        child.counter = self.counter
        # Child does not inherit children, only the causal time (counter)
        self.children[child_id] = child
        return child
    
    def increment(self):
        self.counter += 1
    
    def join(self, other: 'IntervalTreeClock') -> 'IntervalTreeClock':
        """
        Merges another ITC into this one, returning a NEW ITC instance.
        """
        if self.id != other.id:
            # In a real ITC, IDs are implicit or mergeable. 
            # Here we enforce ID match for merging same-node history.
            # If merging different nodes, one would typically merge into a common ancestor.
            # For simplicity, we assume we are merging states of the SAME logical node 
            # (or receiving update for 'self' from elsewhere).
            logger.warning(f"Merging different IDs: {self.id} vs {other.id}. Result uses {self.id}")

        joined = IntervalTreeClock(self.id)
        joined.counter = max(self.counter, other.counter)
        
        all_keys = set(self.children.keys()) | set(other.children.keys())
        
        for key in all_keys:
            child_self = self.children.get(key)
            child_other = other.children.get(key)
            
            if child_self and child_other:
                joined.children[key] = child_self.join(child_other)
            elif child_self:
                joined.children[key] = child_self.copy()
            else:
                joined.children[key] = child_other.copy()
                
        return joined

    def copy(self) -> 'IntervalTreeClock':
        new_itc = IntervalTreeClock(self.id)
        new_itc.counter = self.counter
        new_itc.children = {k: v.copy() for k, v in self.children.items()}
        return new_itc

    def prune(self):
        """Removes children that provide no additional causal info (same counter as self, no sub-children)."""
        to_remove = []
        for cid, child in self.children.items():
            child.prune()
            if child.counter <= self.counter and not child.children:
                to_remove.append(cid)
        
        for cid in to_remove:
            del self.children[cid]

    def __repr__(self):
        return f"ITC({self.id}, c={self.counter}, ch={len(self.children)})"


class CausalHistory:
    """
    Maintains a history of events associated with causal timestamps.
    """
    
    def __init__(self, actor: str):
        self.actor = actor
        self.dvv = DottedVersionVector(actor)
        self.events: List[Tuple[int, Any]] = []
    
    def record_event(self, data: Any) -> int:
        ts = self.dvv.event()
        self.events.append((ts, data))
        return ts
    
    def merge_history(self, other: 'CausalHistory'):
        if not isinstance(other, CausalHistory):
            raise TypeError("Can only merge with CausalHistory")
        self.dvv.merge(other.dvv)
        # Merging events is application specific (e.g. union, deduplication)
        # Here we just ensure the clock reflects knowledge of 'other'
    
    def get_causal_past(self) -> Set[Tuple[str, int]]:
        return self.dvv.dots.copy() | {(a, t) for a, top in self.dvv.clock.items() for t in range(1, top+1)}

    def __repr__(self):
        return f"CausalHistory({self.actor}, events={len(self.events)})"