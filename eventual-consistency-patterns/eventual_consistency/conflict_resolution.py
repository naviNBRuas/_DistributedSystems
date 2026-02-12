from typing import Callable, Any
from .models import VersionedValue, VectorClock, Ordering

def resolve_lww(v1: VersionedValue, v2: VersionedValue) -> VersionedValue:
    """
    Last-Write-Wins conflict resolution.
    Returns the value with the higher timestamp.
    """
    if v1.timestamp > v2.timestamp:
        return v1
    elif v2.timestamp > v1.timestamp:
        return v2
    else:
        # Tie-breaker (e.g., lexicographical on value representation or arbitrary)
        return v1 

def resolve_vector_clock(
    v1: VersionedValue, 
    v2: VersionedValue, 
    merge_func: Callable[[Any, Any], Any] = None
) -> VersionedValue:
    """
    Resolves conflict using Vector Clocks.
    If one happens-before the other, returns the later one.
    If concurrent, uses merge_func to resolve. If merge_func is None, raises Exception or defaults to LWW.
    """
    ordering = v1.vector_clock.compare(v2.vector_clock)
    
    if ordering == Ordering.GT:
        return v1
    elif ordering == Ordering.LT:
        return v2
    elif ordering == Ordering.EQ:
        return v1 # Same
    else: # CONCURRENT
        if merge_func:
            merged_val = merge_func(v1.value, v2.value)
            # Create a new versioned value with merged clock and current time
            new_clock = v1.vector_clock.copy()
            new_clock.merge(v2.vector_clock)
            return VersionedValue(value=merged_val, vector_clock=new_clock)
        else:
            # Fallback to LWW if no merge strategy provided
            return resolve_lww(v1, v2)
