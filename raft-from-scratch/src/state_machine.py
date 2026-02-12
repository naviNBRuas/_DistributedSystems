"""
State Machine Interface and Example Implementations

Defines the abstract interface for state machines that can be
replicated using Raft consensus.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import pickle


class StateMachine(ABC):
    """
    Abstract interface for state machines that use Raft consensus
    
    Implementations must be deterministic - applying the same command
    sequence must always produce the same state.
    """
    
    @abstractmethod
    def apply(self, command: dict) -> Any:
        """
        Apply a committed command to the state machine
        
        Args:
            command: The command to apply (must be deterministic)
            
        Returns:
            The result of applying the command
        """
        pass
    
    @abstractmethod
    def snapshot(self) -> bytes:
        """
        Create a snapshot of the current state
        
        Returns:
            Serialized snapshot that can be restored later
        """
        pass
    
    @abstractmethod
    def restore(self, snapshot: bytes) -> None:
        """
        Restore state from a snapshot
        
        Args:
            snapshot: Previously created snapshot
        """
        pass


class KeyValueStateMachine(StateMachine):
    """
    Simple key-value store state machine
    
    Supports operations:
    - set: {"op": "set", "key": "foo", "value": "bar"}
    - get: {"op": "get", "key": "foo"}
    - delete: {"op": "delete", "key": "foo"}
    """
    
    def __init__(self):
        self.store: Dict[str, Any] = {}
    
    def apply(self, command: dict) -> Any:
        """Apply a command to the key-value store"""
        op = command.get("op")
        
        if op == "set":
            key = command["key"]
            value = command["value"]
            self.store[key] = value
            return {"status": "ok", "key": key}
        
        elif op == "get":
            key = command["key"]
            value = self.store.get(key)
            return {"status": "ok", "value": value}
        
        elif op == "delete":
            key = command["key"]
            if key in self.store:
                del self.store[key]
                return {"status": "ok", "deleted": True}
            return {"status": "ok", "deleted": False}
        
        else:
            return {"status": "error", "message": f"Unknown operation: {op}"}
    
    def snapshot(self) -> bytes:
        """Create a snapshot of the store"""
        return pickle.dumps(self.store)
    
    def restore(self, snapshot: bytes) -> None:
        """Restore store from snapshot"""
        self.store = pickle.loads(snapshot)


class CounterStateMachine(StateMachine):
    """
    Distributed counter state machine
    
    Supports operations:
    - increment: {"op": "increment", "delta": 1}
    - get: {"op": "get"}
    """
    
    def __init__(self):
        self.value = 0
    
    def apply(self, command: dict) -> Any:
        """Apply a command to the counter"""
        op = command.get("op")
        
        if op == "increment":
            delta = command.get("delta", 1)
            self.value += delta
            return {"status": "ok", "value": self.value}
        
        elif op == "get":
            return {"status": "ok", "value": self.value}
        
        else:
            return {"status": "error", "message": f"Unknown operation: {op}"}
    
    def snapshot(self) -> bytes:
        """Create a snapshot of the counter"""
        return str(self.value).encode()
    
    def restore(self, snapshot: bytes) -> None:
        """Restore counter from snapshot"""
        self.value = int(snapshot.decode())
