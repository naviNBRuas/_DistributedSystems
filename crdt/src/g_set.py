from typing import Set, Any, List
import json
from crdt_base import CRDT


class GSet(CRDT):
    """
    Grow-Only Set CRDT.
    
    State: Set of elements.
    Operations: add.
    Merge: Set union.
    Query: Get all elements.
    
    Elements added to the set are never removed.
    """
    
    def __init__(self):
        """Initialize an empty G-Set."""
        self._elements: Set[Any] = set()
    
    def add(self, element: Any) -> None:
        """
        Add an element to the set.
        
        Args:
            element: The element to add. Must be hashable.
        """
        self._elements.add(element)
    
    def value(self) -> Set[Any]:
        """
        Get all elements in the set.
        
        Returns:
            A copy of the set of elements.
        """
        return self._elements.copy()
    
    def merge(self, other: 'GSet') -> None:
        """
        Merge with another G-Set.
        
        Args:
            other: Another G-Set to merge with.
        """
        if not isinstance(other, GSet):
            raise TypeError("Cannot merge with non-GSet")
        
        self._elements.update(other._elements)
        
    def to_json(self) -> str:
        """Serialize to JSON."""
        # Convert set to list for JSON serialization
        return json.dumps(list(self._elements))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GSet':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        gset = cls()
        gset._elements = set(data)
        return gset
        
    def __repr__(self) -> str:
        return f"GSet({self._elements})"
