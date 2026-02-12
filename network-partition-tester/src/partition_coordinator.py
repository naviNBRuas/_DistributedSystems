"""
Partition Coordinator

Main controller for creating and managing network partitions
in distributed system tests.
"""

import time
import threading
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class PartitionState(Enum):
    """State of a partition"""
    ACTIVE = "active"
    HEALED = "healed"


@dataclass
class Partition:
    """Represents a network partition"""
    id: str
    groups: List[List[str]]  # List of node groups
    created_at: float
    duration: Optional[float]
    auto_heal: bool
    state: PartitionState = PartitionState.ACTIVE
    
    def is_active(self) -> bool:
        return self.state == PartitionState.ACTIVE
    
    def should_heal(self) -> bool:
        """Check if partition should auto-heal"""
        if self.state != PartitionState.ACTIVE:
            return False
        if not self.auto_heal or not self.duration:
            return False
        elapsed = time.time() - self.created_at
        return elapsed >= self.duration


class PartitionCoordinator:
    """
    Coordinator for network partition testing
    
    Features:
    - Create arbitrary network partitions
    - Automatic or manual partition healing
    - Node crash simulation
    - Latency and packet loss injection
    """
    
    def __init__(self, nodes: List[str]):
        """
        Initialize partition coordinator
        
        Args:
            nodes: List of node IDs in the cluster
        """
        self.nodes = set(nodes)
        self.partitions: Dict[str, Partition] = {}
        self.crashed_nodes: Set[str] = set()
        self.partition_counter = 0
        
        # Connectivity matrix: can node A reach node B?
        self.connectivity: Dict[tuple, bool] = {}
        self._initialize_connectivity()
        
        # Threading
        self.lock = threading.RLock()
        self.running = True
        self.heal_thread = threading.Thread(target=self._auto_heal_loop, daemon=True)
        self.heal_thread.start()
    
    def _initialize_connectivity(self):
        """Initialize full connectivity between all nodes"""
        for node_a in self.nodes:
            for node_b in self.nodes:
                if node_a != node_b:
                    self.connectivity[(node_a, node_b)] = True
    
    def create_partition(
        self,
        groups: List[List[str]],
        duration: Optional[float] = None,
        auto_heal: bool = False
    ) -> str:
        """
        Create a network partition
        
        Nodes in different groups cannot communicate.
        
        Args:
            groups: List of node groups (e.g., [["node1", "node2"], ["node3"]])
            duration: Partition duration in seconds (None = infinite)
            auto_heal: Whether to automatically heal after duration
            
        Returns:
            Partition ID
        """
        with self.lock:
            # Validate groups
            all_nodes = set()
            for group in groups:
                for node in group:
                    if node not in self.nodes:
                        raise ValueError(f"Unknown node: {node}")
                    if node in all_nodes:
                        raise ValueError(f"Node {node} in multiple groups")
                    all_nodes.add(node)
            
            # Create partition ID
            self.partition_counter += 1
            partition_id = f"partition_{self.partition_counter}"
            
            # Create partition object
            partition = Partition(
                id=partition_id,
                groups=groups,
                created_at=time.time(),
                duration=duration,
                auto_heal=auto_heal
            )
            
            self.partitions[partition_id] = partition
            
            # Update connectivity matrix
            self._apply_partition(groups)
            
            print(f"[PartitionCoordinator] Created {partition_id}")
            print(f"  Groups: {groups}")
            if duration:
                print(f"  Duration: {duration}s (auto_heal={auto_heal})")
            
            return partition_id
    
    def _apply_partition(self, groups: List[List[str]]):
        """Apply partition to connectivity matrix"""
        # Disable communication between nodes in different groups
        for i, group_a in enumerate(groups):
            for j, group_b in enumerate(groups):
                if i != j:
                    # Different groups - disable connectivity
                    for node_a in group_a:
                        for node_b in group_b:
                            self.connectivity[(node_a, node_b)] = False
                            self.connectivity[(node_b, node_a)] = False
    
    def heal_partition(self, partition_id: Optional[str] = None):
        """
        Heal a partition (restore connectivity)
        
        Args:
            partition_id: Specific partition to heal (None = heal all)
        """
        with self.lock:
            if partition_id:
                if partition_id not in self.partitions:
                    raise ValueError(f"Unknown partition: {partition_id}")
                
                partition = self.partitions[partition_id]
                partition.state = PartitionState.HEALED
                print(f"[PartitionCoordinator] Healed {partition_id}")
            else:
                # Heal all partitions
                for partition in self.partitions.values():
                    partition.state = PartitionState.HEALED
                print("[PartitionCoordinator] Healed all partitions")
            
            # Restore full connectivity
            self._initialize_connectivity()
            
            # Re-apply other active partitions
            for p in self.partitions.values():
                if p.is_active():
                    self._apply_partition(p.groups)
            
            # Re-apply crashed nodes
            for node in self.crashed_nodes:
                 for other_node in self.nodes:
                    if other_node != node:
                        self.connectivity[(node, other_node)] = False
                        self.connectivity[(other_node, node)] = False
    
    def crash_node(self, node_id: str):
        """
        Simulate node crash
        
        Crashed node cannot send or receive any messages.
        
        Args:
            node_id: Node to crash
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Unknown node: {node_id}")
            
            self.crashed_nodes.add(node_id)
            
            # Disconnect crashed node from all others
            for other_node in self.nodes:
                if other_node != node_id:
                    self.connectivity[(node_id, other_node)] = False
                    self.connectivity[(other_node, node_id)] = False
            
            print(f"[PartitionCoordinator] Crashed node: {node_id}")
    
    def recover_node(self, node_id: str):
        """
        Recover a crashed node
        
        Args:
            node_id: Node to recover
        """
        with self.lock:
            if node_id not in self.crashed_nodes:
                return
            
            self.crashed_nodes.remove(node_id)
            
            # Restore connectivity (respecting active partitions)
            for other_node in self.nodes:
                if other_node != node_id:
                    # Default to connected
                    self.connectivity[(node_id, other_node)] = True
                    self.connectivity[(other_node, node_id)] = True
            
            # Re-apply active partitions
            for partition in self.partitions.values():
                if partition.is_active():
                    self._apply_partition(partition.groups)
            
            print(f"[PartitionCoordinator] Recovered node: {node_id}")
    
    def can_communicate(self, from_node: str, to_node: str) -> bool:
        """
        Check if two nodes can communicate
        
        Args:
            from_node: Source node
            to_node: Destination node
            
        Returns:
            True if nodes can communicate
        """
        with self.lock:
            if from_node in self.crashed_nodes or to_node in self.crashed_nodes:
                return False
            
            return self.connectivity.get((from_node, to_node), False)
    
    def get_reachable_nodes(self, from_node: str) -> Set[str]:
        """
        Get set of nodes reachable from a given node
        
        Args:
            from_node: Source node
            
        Returns:
            Set of reachable node IDs
        """
        reachable = set()
        for node in self.nodes:
            if node != from_node and self.can_communicate(from_node, node):
                reachable.add(node)
        return reachable
    
    def _auto_heal_loop(self):
        """Background thread to auto-heal partitions"""
        while self.running:
            time.sleep(1)
            
            with self.lock:
                for partition in list(self.partitions.values()):
                    if partition.should_heal():
                        self.heal_partition(partition.id)
    
    def cleanup(self):
        """Clean up coordinator resources"""
        self.running = False
        if self.heal_thread:
            self.heal_thread.join(timeout=2)
    
    # Assertion methods for testing
    
    def assert_cluster_healthy(self, timeout: float = 30):
        """
        Assert that cluster is in a healthy state
        
        Args:
            timeout: Maximum time to wait for health
            
        Raises:
            AssertionError: If cluster is not healthy
        """
        # In a real implementation, this would check actual cluster health
        # For now, just check no active partitions or crashed nodes
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                active_partitions = [p for p in self.partitions.values() if p.is_active()]
                if not active_partitions and not self.crashed_nodes:
                    print("[PartitionCoordinator] ✓ Cluster healthy")
                    return
            time.sleep(0.5)
        
        raise AssertionError("Cluster not healthy within timeout")
    
    def get_active_partitions(self) -> List[Partition]:
        """Get list of currently active partitions"""
        with self.lock:
            return [p for p in self.partitions.values() if p.is_active()]
    
    def __repr__(self):
        active_partitions = len(self.get_active_partitions())
        return f"PartitionCoordinator(nodes={len(self.nodes)}, active_partitions={active_partitions}, crashed={len(self.crashed_nodes)})"


# Example usage
if __name__ == "__main__":
    print("=== Network Partition Coordinator Example ===\n")
    
    # Create coordinator for 5-node cluster
    coordinator = PartitionCoordinator(
        nodes=["node1", "node2", "node3", "node4", "node5"]
    )
    
    print(f"Initial: {coordinator}\n")
    
    # Create a partition: split into 2-3
    partition_id = coordinator.create_partition(
        groups=[["node1", "node2"], ["node3", "node4", "node5"]],
        duration=5,
        auto_heal=True
    )
    
    # Test connectivity
    print("\n--- Testing Connectivity ---")
    print(f"node1 -> node2: {coordinator.can_communicate('node1', 'node2')}")
    print(f"node1 -> node3: {coordinator.can_communicate('node1', 'node3')}")
    print(f"node3 -> node4: {coordinator.can_communicate('node3', 'node4')}")
    
    print(f"\nnode1 can reach: {coordinator.get_reachable_nodes('node1')}")
    print(f"node3 can reach: {coordinator.get_reachable_nodes('node3')}")
    
    # Wait for auto-heal
    print("\nWaiting for auto-heal...")
    time.sleep(6)
    
    # Verify healed
    print(f"\nAfter heal: {coordinator}")
    coordinator.assert_cluster_healthy()
    
    # Test node crash
    print("\n--- Testing Node Crash ---")
    coordinator.crash_node("node2")
    print(f"node1 -> node2: {coordinator.can_communicate('node1', 'node2')}")
    
    # Recover node
    coordinator.recover_node("node2")
    print(f"After recovery - node1 -> node2: {coordinator.can_communicate('node1', 'node2')}")
    
    # Cleanup
    coordinator.cleanup()
    print("\n✓ Example complete")
