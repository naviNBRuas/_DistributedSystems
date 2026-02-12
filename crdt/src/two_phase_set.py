from typing import Set, Any
import json
from crdt_base import CRDT
from g_set import GSet


class TwoPhaseSet(CRDT):
    """
    Two-Phase Set (2P-Set) CRDT.
    
    State: Two G-Sets (added, removed).
    Operations: add, remove.
    Merge: Merge added sets and removed sets.
    Query: added - removed.
    
    Constraint: An element can be added and then removed, but never re-added.
    """
    
    def __init__(self):
        """Initialize an empty 2P-Set."""
        self.added = GSet()
        self.removed = GSet()
    
    def add(self, element: Any) -> None:
        """
        Add an element to the set.
        
        Args:
            element: The element to add.
        """
        if element in self.removed.value():
            # Cannot re-add a removed element
            return
        self.added.add(element)
    
    def remove(self, element: Any) -> None:
        """
        Remove an element from the set.
        
        Args:
            element: The element to remove.
        """
        if element in self.added.value():
            self.removed.add(element)
        # If strictly following 2P-Set, we might allow removing things not yet added (tombstoning preemptively),
        # but usually it makes sense to only remove what is known.
        # However, for convergence, if we receive a remove for something we haven't seen added yet,
        # we should still record the removal (tombstone).
        # So actually, we should just add to removed set regardless.
        self.removed.add(element)

    def value(self) -> Set[Any]:
        """
        Get current elements in the set.
        
        Returns:
            Set of elements that are in 'added' but not in 'removed'.
        """
        return self.added.value() - self.removed.value()
    
    def merge(self, other: 'TwoPhaseSet') -> None:
        """
        Merge with another 2P-Set.
        
        Args:
            other: Another 2P-Set to merge with.
        """
        if not isinstance(other, TwoPhaseSet):
            raise TypeError("Cannot merge with non-TwoPhaseSet")
            
        self.added.merge(other.added)
        self.removed.merge(other.removed)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'added': json.loads(self.added.to_json()),
            'removed': json.loads(self.removed.to_json())
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TwoPhaseSet':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        tpset = cls()
        
        # We can reconstruct GSets from lists
        # GSet.from_json expects a JSON string of a list
        tpset.added = GSet.from_json(json.dumps(data['added']))
        tpset.removed = GSet.from_json(json.dumps(data['removed']))
        return tpset
        
    def __repr__(self) -> str:
        return f"TwoPhaseSet({self.value()})"
