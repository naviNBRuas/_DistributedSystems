from typing import List, Optional
from storage import Storage, LogEntry

class RaftLog:
    """
    Manages the replicated log, including persistence and compaction (snapshots).
    
    Raft uses 1-based indexing for log entries. 
    However, internally we might store them in a 0-indexed list.
    This class abstracts that detail.
    """
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self.entries: List[LogEntry] = []
        
        # Snapshot state
        self.last_included_index = 0
        self.last_included_term = 0
        
        self._load()
        
    def _load(self):
        """Load log and snapshot metadata from storage"""
        self.entries = self.storage.load_log()
        _, self.last_included_index, self.last_included_term = self.storage.load_snapshot()
        
    def persist(self):
        """Persist current log entries to storage"""
        self.storage.save_log(self.entries)
        
    def __len__(self):
        """Return the index of the last entry in the log"""
        return self.last_included_index + len(self.entries)
    
    def __getitem__(self, index: int) -> LogEntry:
        """Get entry by its absolute index (1-based)"""
        if index <= self.last_included_index:
            raise IndexError(f"Index {index} is part of the snapshot (last_included={self.last_included_index})")
        
        internal_index = index - self.last_included_index - 1
        if internal_index < 0 or internal_index >= len(self.entries):
             raise IndexError(f"Log index {index} out of range (size={len(self)})")
             
        return self.entries[internal_index]
        
    def get_term(self, index: int) -> int:
        """Get term of entry at index. Returns 0 if index is 0. Handles snapshot indices."""
        if index == 0:
            return 0
        if index == self.last_included_index:
            return self.last_included_term
        if index < self.last_included_index:
             # In a real implementation we might throw, or just return the snapshot term if we are sure?
             # For safety, we assume we don't query terms deep inside snapshot unless checking for consistency
             return self.last_included_term # Approximation or Error?
             # Ideally we shouldn't need terms from inside the snapshot for core logic
        
        return self[index].term

    def append(self, entry: LogEntry):
        """Append a new entry"""
        self.entries.append(entry)
        self.persist()
        
    def get_entries(self, start_index: int) -> List[LogEntry]:
        """Get entries starting from start_index (inclusive)"""
        if start_index <= self.last_included_index:
             # If we need entries that are compacted, we might need to send a snapshot instead.
             # This method returns available log entries.
             start_index = self.last_included_index + 1
             
        internal_start = start_index - self.last_included_index - 1
        return self.entries[internal_start:]
    
    def truncate(self, index: int):
        """Delete entries from index (inclusive) onwards"""
        if index <= self.last_included_index:
            # We can't truncate inside the snapshot. 
            # This generally implies a follower is receiving an old snapshot or something weird.
            # We'll re-sync via snapshot mechanism separately.
            return 
            
        internal_index = index - self.last_included_index - 1
        if internal_index < len(self.entries):
            self.entries = self.entries[:internal_index]
            self.persist()

    def match_log(self, prev_log_index: int, prev_log_term: int) -> bool:
        """Check if log contains an entry at prev_log_index with prev_log_term"""
        if prev_log_index == 0:
            return True
            
        if prev_log_index > len(self):
            return False
            
        # Check term
        # Note: get_term handles index == last_included_index
        if self.get_term(prev_log_index) != prev_log_term:
            return False
            
        return True

    def compact(self, last_index: int, last_term: int, snapshot_bytes: bytes):
        """Compact log up to last_index"""
        if last_index <= self.last_included_index:
            return
            
        # Find where to cut
        internal_index = last_index - self.last_included_index - 1
        
        # Keep entries after last_index
        if internal_index < len(self.entries) - 1:
            self.entries = self.entries[internal_index + 1:]
        else:
            self.entries = []
            
        self.last_included_index = last_index
        self.last_included_term = last_term
        
        self.storage.save_snapshot(snapshot_bytes, last_index, last_term)
        self.persist() # Save the truncated log
