import time
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class StateEntry:
    key: str
    value: Any
    version: int
    timestamp: float
    node_id: str
    tombstone: bool = False

class StateStore:
    """
    Thread-safe store for gossip state with versioning.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._store: Dict[str, StateEntry] = {}
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Any]] = {} # Simple pattern -> callback list

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry and not entry.tombstone:
                return entry.value
            return None

    def get_entry(self, key: str) -> Optional[StateEntry]:
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, value: Any) -> StateEntry:
        with self._lock:
            existing = self._store.get(key)
            version = (existing.version + 1) if existing else 1
            entry = StateEntry(
                key=key,
                value=value,
                version=version,
                timestamp=time.time(),
                node_id=self.node_id
            )
            self._store[key] = entry
            return entry

    def delete(self, key: str) -> Optional[StateEntry]:
        with self._lock:
            existing = self._store.get(key)
            if not existing or existing.tombstone:
                return None
            
            entry = StateEntry(
                key=key,
                value=None,
                version=existing.version + 1,
                timestamp=time.time(),
                node_id=self.node_id,
                tombstone=True
            )
            self._store[key] = entry
            return entry

    def merge(self, entry: StateEntry) -> bool:
        """
        Merge an entry from another node.
        Returns True if the entry was applied (newer).
        """
        with self._lock:
            existing = self._store.get(entry.key)
            
            if existing:
                if entry.version > existing.version:
                    self._store[entry.key] = entry
                    return True
                elif entry.version == existing.version:
                    # Tie-breaking logic (e.g., compare node_ids or timestamps)
                    # For simplicity, prefer higher node_id
                    if entry.node_id > existing.node_id:
                         self._store[entry.key] = entry
                         return True
            else:
                self._store[entry.key] = entry
                return True
            
            return False

    def get_all_entries(self) -> List[StateEntry]:
        with self._lock:
            return list(self._store.values())

    def get_digest(self) -> Dict[str, int]:
        with self._lock:
            return {key: entry.version for key, entry in self._store.items()}
    
    def get_delta(self, digest: Dict[str, int]) -> List[StateEntry]:
        """Return entries that are newer than what is in the digest."""
        delta = []
        with self._lock:
            for key, entry in self._store.items():
                peer_version = digest.get(key, 0)
                if entry.version > peer_version:
                    delta.append(entry)
        return delta
