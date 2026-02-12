from typing import Set, Any, Tuple, List, Dict
import json
import uuid
from crdt_base import CRDT


class ORSet(CRDT):
    """
    Observed-Remove Set (OR-Set) CRDT.
    
    State: Two sets of (element, unique_tag) tuples.
    Operations: add, remove.
    Merge: Union of add_sets and remove_sets.
    Query: Elements in add_set but not in remove_set.
    
    Properties:
    - Add-wins semantics (in case of concurrent add/remove of same element, 
      if the remove didn't see the specific add instance, the add wins).
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        # We store (element, tag) tuples.
        # Note: Elements must be hashable and JSON serializable.
        self._add_set: Set[Tuple[Any, str]] = set()
        self._remove_set: Set[Tuple[Any, str]] = set()
        
    def add(self, element: Any) -> None:
        """
        Add an element to the set.
        Generates a unique tag for this addition.
        """
        tag = str(uuid.uuid4())
        self._add_set.add((element, tag))
        
    def remove(self, element: Any) -> None:
        """
        Remove an element from the set.
        Removes all instances of the element that are currently observed.
        """
        # Find all tags for this element currently in the effective set
        observed_instances = {
            (e, t) for (e, t) in self._add_set 
            if e == element and (e, t) not in self._remove_set
        }
        
        # Add them to the remove set
        self._remove_set.update(observed_instances)
        
    def value(self) -> Set[Any]:
        """
        Get current elements in the set.
        """
        active_instances = self._add_set - self._remove_set
        return {e for e, t in active_instances}
        
    def elements(self) -> Set[Any]:
        """Alias for value() to match README examples."""
        return self.value()
    
    def merge(self, other: 'ORSet') -> None:
        """
        Merge with another OR-Set.
        """
        if not isinstance(other, ORSet):
            raise TypeError("Cannot merge with non-ORSet")
            
        self._add_set.update(other._add_set)
        self._remove_set.update(other._remove_set)
        
    def to_json(self) -> str:
        """Serialize to JSON."""
        # Sets of tuples are not directly JSON serializable.
        # Convert to list of lists: [ [elem, tag], ... ]
        return json.dumps({
            'node_id': self.node_id,
            'add_set': list(self._add_set),
            'remove_set': list(self._remove_set)
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ORSet':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        orset = cls(data['node_id'])
        
        # Convert lists back to sets of tuples
        # JSON loads lists as lists, we need tuples for the set
        if data['add_set']:
            orset._add_set = set(tuple(x) for x in data['add_set'])
        
        if data['remove_set']:
            orset._remove_set = set(tuple(x) for x in data['remove_set'])
            
        return orset

    def __repr__(self) -> str:
        return f"ORSet({self.value()})"
