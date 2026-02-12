import os
import pickle
import threading
from abc import ABC, abstractmethod
from typing import List, Optional, Any
from dataclasses import dataclass

@dataclass
class LogEntry:
    """A single entry in the replicated log"""
    term: int
    index: int
    command: dict
    
    def __repr__(self):
        return f"LogEntry(term={self.term}, index={self.index}, cmd={self.command})"

class Storage(ABC):
    """Abstract interface for Raft persistent storage"""
    
    @abstractmethod
    def save_state(self, current_term: int, voted_for: Optional[str]):
        """Save current_term and voted_for"""
        pass
    
    @abstractmethod
    def load_state(self) -> tuple[int, Optional[str]]:
        """Load current_term and voted_for. Returns (term, voted_for)"""
        pass
        
    @abstractmethod
    def save_log(self, log: List[LogEntry]):
        """Save the entire log (or append entries)"""
        pass
    
    @abstractmethod
    def load_log(self) -> List[LogEntry]:
        """Load the entire log"""
        pass
    
    @abstractmethod
    def save_snapshot(self, snapshot: bytes, last_included_index: int, last_included_term: int):
        """Save a state machine snapshot and metadata"""
        pass
    
    @abstractmethod
    def load_snapshot(self) -> tuple[Optional[bytes], int, int]:
        """Load snapshot. Returns (snapshot_bytes, last_included_index, last_included_term)"""
        pass

class FileStorage(Storage):
    """File-based implementation of Raft storage using pickle"""
    
    def __init__(self, base_path: str, node_id: str):
        self.base_path = base_path
        self.node_id = node_id
        
        # Ensure directory exists
        os.makedirs(base_path, exist_ok=True)
        
        self.state_file = os.path.join(base_path, f"raft_state_{node_id}.pkl")
        self.log_file = os.path.join(base_path, f"raft_log_{node_id}.pkl")
        self.snapshot_file = os.path.join(base_path, f"raft_snapshot_{node_id}.pkl")
        self.lock = threading.RLock()
        
    def save_state(self, current_term: int, voted_for: Optional[str]):
        with self.lock:
            with open(self.state_file, 'wb') as f:
                pickle.dump({'current_term': current_term, 'voted_for': voted_for}, f)
                
    def load_state(self) -> tuple[int, Optional[str]]:
        with self.lock:
            if not os.path.exists(self.state_file):
                return 0, None
            try:
                with open(self.state_file, 'rb') as f:
                    data = pickle.load(f)
                    return data.get('current_term', 0), data.get('voted_for')
            except (EOFError, pickle.UnpicklingError):
                return 0, None

    def save_log(self, log: List[LogEntry]):
        # Naive implementation: overwrite file every time. 
        # Production would use an append-only file or distinct segment files.
        with self.lock:
            with open(self.log_file, 'wb') as f:
                pickle.dump(log, f)
                
    def load_log(self) -> List[LogEntry]:
        with self.lock:
            if not os.path.exists(self.log_file):
                return []
            try:
                with open(self.log_file, 'rb') as f:
                    return pickle.load(f)
            except (EOFError, pickle.UnpicklingError):
                return []

    def save_snapshot(self, snapshot: bytes, last_included_index: int, last_included_term: int):
        with self.lock:
            with open(self.snapshot_file, 'wb') as f:
                data = {
                    'snapshot': snapshot,
                    'last_included_index': last_included_index,
                    'last_included_term': last_included_term
                }
                pickle.dump(data, f)
                
    def load_snapshot(self) -> tuple[Optional[bytes], int, int]:
        with self.lock:
            if not os.path.exists(self.snapshot_file):
                return None, 0, 0
            try:
                with open(self.snapshot_file, 'rb') as f:
                    data = pickle.load(f)
                    return data['snapshot'], data['last_included_index'], data['last_included_term']
            except (EOFError, pickle.UnpicklingError):
                return None, 0, 0
