from typing import Dict, Any, Optional, List
import json
import time
from crdt_base import CRDT
from lww_register import LWWRegister


class LWWMap(CRDT):
    """
    Last-Write-Wins Map CRDT.
    
    State: Map of Key -> LWWRegister.
    Operations: put, remove, get.
    Merge: Merge registers for each key.
    Query: Get value by key.
    
    This implementation handles element addition and removal via LWWRegisters.
    A removal is modeled as writing a specific tombstone value (None) or 
    keeping the register but treating the key as missing if the value is None.
    However, standard LWW-Map usually treats removal as a write with a timestamp.
    """
    
    def __init__(self, node_id: str):
        """
        Initialize LWW-Map.
        
        Args:
            node_id: Unique identifier for this replica.
        """
        self.node_id = node_id
        # We store registers directly. 
        # Key -> LWWRegister(value)
        self._registers: Dict[str, LWWRegister] = {}
        
    def put(self, key: str, value: Any, timestamp: float = None) -> None:
        """
        Set a value for a key.
        
        Args:
            key: Map key.
            value: Value to store.
            timestamp: Timestamp of the operation.
        """
        if timestamp is None:
            timestamp = time.time()
            
        if key not in self._registers:
            self._registers[key] = LWWRegister(self.node_id, value, timestamp)
        else:
            self._registers[key].write(value, timestamp)
            
    def get(self, key: str) -> Optional[Any]:
        """
        Get value for a key.
        
        Returns:
            The value, or None if key doesn't exist or was removed (is None).
        """
        if key not in self._registers:
            return None
        return self._registers[key].value()
    
    def remove(self, key: str, timestamp: float = None) -> None:
        """
        Remove a key.
        
        Args:
            key: Key to remove.
            timestamp: Timestamp of removal.
        """
        # In LWW-Map, removal is a write of a tombstone (None).
        self.put(key, None, timestamp)
        
    def value(self) -> Dict[str, Any]:
        """
        Get all current key-value pairs (excluding tombstones).
        
        Returns:
            Dictionary of active keys and values.
        """
        result = {}
        for key, reg in self._registers.items():
            val = reg.value()
            if val is not None:
                result[key] = val
        return result
        
    def merge(self, other: 'LWWMap') -> None:
        """
        Merge with another LWW-Map.
        
        Args:
            other: Another LWW-Map to merge with.
        """
        if not isinstance(other, LWWMap):
            raise TypeError("Cannot merge with non-LWWMap")
            
        for key, other_reg in other._registers.items():
            if key not in self._registers:
                # If we don't have it, we copy it.
                # We need a deep copy or just reconstruct it to avoid shared mutable state issues
                # simpler to use to_json/from_json or just create new register
                # Assuming LWWRegister is properly encapsulated, we can just use merge logic.
                # But here we are instantiating a new register for our node_id but with the OTHER's state?
                # Actually, the register keeps track of who wrote it. 
                # So we should copy the register state exactly.
                new_reg = LWWRegister.from_json(other_reg.to_json())
                self._registers[key] = new_reg
            else:
                self._registers[key].merge(other_reg)
                
    def to_json(self) -> str:
        """Serialize to JSON."""
        # Convert registers to dict of json strings or dicts
        registers_data = {k: json.loads(v.to_json()) for k, v in self._registers.items()}
        return json.dumps({
            'node_id': self.node_id,
            'registers': registers_data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LWWMap':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        lww_map = cls(data['node_id'])
        
        registers_data = data['registers']
        for key, reg_data in registers_data.items():
            # We need to turn the dict back into a JSON string for LWWRegister.from_json
            # Or make LWWRegister.from_json accept a dict (which it currently doesn't, it takes str)
            reg_json = json.dumps(reg_data)
            lww_map._registers[key] = LWWRegister.from_json(reg_json)
            
        return lww_map

    def __repr__(self) -> str:
        return f"LWWMap({self.value()})"
