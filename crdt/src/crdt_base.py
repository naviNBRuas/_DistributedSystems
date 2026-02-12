from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar

T = TypeVar('T', bound='CRDT')

class CRDT(ABC):
    """
    Abstract Base Class for Conflict-free Replicated Data Types (CRDTs).
    
    All CRDTs must implement:
    1. value(): Get the current logical value
    2. merge(other): Merge state with another replica
    3. to_json() / from_json(): Serialization
    """
    
    @abstractmethod
    def value(self) -> Any:
        """Get the current value of the CRDT."""
        pass
    
    @abstractmethod
    def merge(self, other: 'CRDT') -> None:
        """
        Merge the state of another CRDT into this one.
        
        Args:
            other: The other CRDT instance to merge from.
        """
        pass
    
    @abstractmethod
    def to_json(self) -> str:
        """Serialize the CRDT state to a JSON string."""
        pass
    
    @classmethod
    @abstractmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """
        Create a CRDT instance from a JSON string.
        
        Args:
            json_str: The JSON string representation of the CRDT state.
            
        Returns:
            An instance of the CRDT.
        """
        pass
