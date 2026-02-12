from typing import List, Protocol, Any, Optional
import concurrent.futures
from .models import VersionedValue
from .conflict_resolution import resolve_lww

class Replica(Protocol):
    """
    Protocol defining the interface for a replica in the system.
    """
    def get(self, key: str) -> Optional[VersionedValue]:
        ...
    
    def put(self, key: str, value: VersionedValue) -> None:
        ...

class ReadRepair:
    """
    Implements the Read Repair pattern with asynchronous background repairs.
    """
    def __init__(self, replicas: List[Replica], max_workers: int = 5):
        self.replicas = replicas
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def read(self, key: str) -> Optional[VersionedValue]:
        """
        Reads a key from all replicas, determines the latest version,
        and schedules repairs for stale replicas in the background.
        """
        # Parallel read to reduce latency
        # We use a separate executor or the same one? Ideally separate for IO bound.
        # For simplicity, let's keep reads synchronous (or parallel wait) and repairs fire-and-forget.
        
        # Parallel read implementation:
        futures = {self._executor.submit(self._safe_get, replica, key): replica for replica in self.replicas}
        
        valid_results = []
        replica_results = [] # Tuples of (replica, value)

        for future in concurrent.futures.as_completed(futures):
            replica = futures[future]
            try:
                val = future.result()
                replica_results.append((replica, val))
                if val is not None:
                    valid_results.append(val)
            except Exception:
                 replica_results.append((replica, None))
        
        if not valid_results:
            return None

        # Resolve conflict (find latest)
        latest = valid_results[0]
        for val in valid_results[1:]:
            latest = resolve_lww(latest, val)
            
        # Schedule Repair asynchronously
        self._executor.submit(self._repair_stale, key, latest, replica_results)

        return latest

    def _safe_get(self, replica: Replica, key: str) -> Optional[VersionedValue]:
        try:
            return replica.get(key)
        except Exception:
            return None

    def _repair_stale(self, key: str, latest: VersionedValue, replica_results: List[Any]):
        """
        Background task to repair stale replicas.
        """
        for replica, val in replica_results:
            should_repair = False
            if val is None:
                should_repair = True
            elif val.timestamp < latest.timestamp:
                should_repair = True
            
            if should_repair:
                try:
                    replica.put(key, latest)
                except Exception:
                    pass # Best effort repair
    
    def shutdown(self):
        self._executor.shutdown(wait=True)
