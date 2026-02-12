"""
Deadlock Detector Implementation

Provides deadlock detection and resolution mechanisms for
distributed systems using Wait-For Graphs.
"""

import time
import threading
from typing import Dict, List, Set, Optional, Tuple


class DeadlockDetector:
    """
    Detects deadlocks using a Wait-For Graph (WFG).
    
    A deadlock exists if there is a cycle in the WFG.
    The graph tracks which process is waiting for which resource,
    and which process holds which resource.
    """
    
    def __init__(self):
        self.lock = threading.RLock()
        # Maps process_id -> set of resource_ids it is waiting for
        self.waiting_for: Dict[str, Set[str]] = {}
        # Maps resource_id -> process_id that holds it
        self.held_by: Dict[str, str] = {}
        # Maps process_id -> set of resource_ids it holds
        self.holding: Dict[str, Set[str]] = {}
        # Explicit lock ordering to prevent deadlocks (optional)
        self.lock_order: List[str] = []
        
    def record_lock_order(self, process_id: str, resource_id: str):
        """
        Record that a process successfully acquired a lock.
        """
        with self.lock:
            # Update held_by
            self.held_by[resource_id] = process_id
            
            # Update holding
            if process_id not in self.holding:
                self.holding[process_id] = set()
            self.holding[process_id].add(resource_id)
            
            # If process was waiting for this resource, remove from waiting_for
            if process_id in self.waiting_for and resource_id in self.waiting_for[process_id]:
                self.waiting_for[process_id].remove(resource_id)
                if not self.waiting_for[process_id]:
                    del self.waiting_for[process_id]

    def record_wait(self, process_id: str, resource_id: str):
        """
        Record that a process is waiting for a resource.
        """
        with self.lock:
            if process_id not in self.waiting_for:
                self.waiting_for[process_id] = set()
            self.waiting_for[process_id].add(resource_id)
            
    def release_lock(self, process_id: str, resource_id: str):
        """
        Record that a process released a lock.
        """
        with self.lock:
            if resource_id in self.held_by and self.held_by[resource_id] == process_id:
                del self.held_by[resource_id]
            
            if process_id in self.holding and resource_id in self.holding[process_id]:
                self.holding[process_id].remove(resource_id)
                if not self.holding[process_id]:
                    del self.holding[process_id]
            
            # Also clear any waits for this resource (though realistically, 
            # the next process would acquire it, but for cleanup)
            # In a real system, the next waiter would acquire it.

    def has_cycle(self) -> bool:
        """
        Check if there is a cycle in the Wait-For Graph.
        """
        with self.lock:
            visited = set()
            recursion_stack = set()
            
            # We need to build the process-to-process graph
            # P1 waits for R1, R1 held by P2 => P1 -> P2
            
            adj: Dict[str, Set[str]] = {}
            
            for p_waiting, resources in self.waiting_for.items():
                for res in resources:
                    if res in self.held_by:
                        p_holding = self.held_by[res]
                        if p_waiting != p_holding:
                            if p_waiting not in adj:
                                adj[p_waiting] = set()
                            adj[p_waiting].add(p_holding)
            
            # DFS to detect cycle
            def dfs(node):
                visited.add(node)
                recursion_stack.add(node)
                
                if node in adj:
                    for neighbor in adj[node]:
                        if neighbor not in visited:
                            if dfs(neighbor):
                                return True
                        elif neighbor in recursion_stack:
                            return True
                
                recursion_stack.remove(node)
                return False

            for node in list(adj.keys()):
                if node not in visited:
                    if dfs(node):
                        return True
                        
            return False

    def get_deadlock_cycle(self) -> List[str]:
        """
        Return the list of processes involved in a deadlock cycle.
        """
        with self.lock:
            # Build graph again
            adj: Dict[str, Set[str]] = {}
            for p_waiting, resources in self.waiting_for.items():
                for res in resources:
                    if res in self.held_by:
                        p_holding = self.held_by[res]
                        if p_waiting != p_holding:
                            if p_waiting not in adj:
                                adj[p_waiting] = set()
                            adj[p_waiting].add(p_holding)
            
            visited = set()
            stack = []
            on_stack = set()
            cycle = []

            def dfs(node):
                visited.add(node)
                stack.append(node)
                on_stack.add(node)

                if node in adj:
                    for neighbor in adj[node]:
                        if neighbor in on_stack:
                            # Cycle detected
                            try:
                                index = stack.index(neighbor)
                                cycle.extend(stack[index:])
                            except ValueError:
                                pass
                            return True
                        if neighbor not in visited:
                            if dfs(neighbor):
                                return True
                
                on_stack.remove(node)
                stack.pop()
                return False

            for node in list(adj.keys()):
                if node not in visited:
                    if dfs(node):
                        return cycle
            return []

    def choose_deadlock_victim(self) -> Optional[str]:
        """
        Choose a process to abort to break the deadlock.
        Simple strategy: return the first process in the cycle.
        """
        cycle = self.get_deadlock_cycle()
        if cycle:
            return cycle[0]
        return None

    def enforce_lock_order(self, resources: List[str]):
        """
        Define a global lock order to prevent deadlocks.
        """
        with self.lock:
            self.lock_order = resources

    def acquire_with_timeout(self, process_id: str, resource_id: str, timeout_sec: float) -> bool:
        """
        Simulation helper: try to acquire with timeout (not real acquisition).
        """
        start = time.time()
        while time.time() - start < timeout_sec:
            with self.lock:
                if resource_id not in self.held_by:
                    self.record_lock_order(process_id, resource_id)
                    return True
            time.sleep(0.1)
        return False
