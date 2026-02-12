from typing import Any, Dict
from .models import VectorClock, VersionedValue

class CausalSession:
    """
    Maintains a client-side vector clock to ensure Causal Consistency (Read-Your-Writes, Monotonic Reads).
    """
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.clock = VectorClock()

    def update_clock(self, other_clock: VectorClock):
        """Update session clock with observed clock."""
        self.clock.merge(other_clock)

    def prepare_write(self) -> VectorClock:
        """
        Increment client's clock and return it for a write operation.
        """
        # In a strict sense, we increment on write.
        # But usually the server increments its own clock component.
        # The client just passes its context.
        # However, if we view this 'client' as a node participant:
        self.clock.increment(self.client_id)
        return self.clock.copy()

    def check_consistency(self, value: VersionedValue) -> bool:
        """
        Checks if the read value satisfies causal consistency (i.e., we haven't seen a future of this value already).
        Actually, for Monotonic Reads: value.clock >= session.clock.
        Wait, if value.clock < session.clock, it's stale.
        """
        # If the value's clock is 'less than' our clock, it might be stale relative to what we've seen.
        # But 'concurrent' is fine.
        # If we have seen {A: 2}, and we read {A: 1}, that is a violation of Monotonic Reads.
        
        # Simple check: Is value.clock >= self.clock?
        # Only check components present in both?
        # A simple causal violation check:
        # For all node k in self.clock: value.clock[k] >= self.clock[k]
        
        for node, time in self.clock.clock.items():
            if value.vector_clock.clock.get(node, 0) < time:
                return False
        return True
