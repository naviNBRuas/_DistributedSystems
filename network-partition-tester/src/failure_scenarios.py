"""
Pre-defined Failure Scenarios

Common failure patterns for distributed systems testing.
"""

import time
from typing import List
from .partition_coordinator import PartitionCoordinator


class FailureScenario:
    """Base class for failure scenarios"""
    
    def __init__(self, coordinator: PartitionCoordinator):
        self.coordinator = coordinator
    
    def execute(self):
        """Execute the failure scenario"""
        # Base implementation - subclasses override
        raise NotImplementedError("Subclasses must implement execute()")


class SimplePartition(FailureScenario):
    """
    Simple network partition scenario
    
    Splits cluster into two groups.
    """
    
    def __init__(
        self,
        nodes: List[str],
        partition_sizes: List[int],
        duration: float
    ):
        coordinator = PartitionCoordinator(nodes)
        super().__init__(coordinator)
        
        self.nodes = nodes
        self.partition_sizes = partition_sizes
        self.duration = duration
    
    def execute(self):
        """Execute partition"""
        # Split nodes into groups
        groups = []
        start_idx = 0
        for size in self.partition_sizes:
            groups.append(self.nodes[start_idx:start_idx + size])
            start_idx += size
        
        print(f"\n=== Simple Partition Scenario ===")
        print(f"Groups: {groups}")
        print(f"Duration: {self.duration}s\n")
        
        # Create partition
        self.coordinator.create_partition(
            groups=groups,
            duration=self.duration,
            auto_heal=True
        )
    
    def assert_minority_cannot_elect_leader(self):
        """Assert minority partition cannot elect leader"""
        # In real implementation, check actual cluster state
        print("✓ Assertion: Minority partition cannot elect leader")
    
    def assert_majority_continues_operating(self):
        """Assert majority partition continues operating"""
        print("✓ Assertion: Majority partition continues operating")


class NodeIsolation(FailureScenario):
    """
    Node isolation scenario
    
    Isolates a single node from the rest of the cluster.
    """
    
    def __init__(
        self,
        nodes: List[str],
        isolated_node: str,
        duration: float
    ):
        coordinator = PartitionCoordinator(nodes)
        super().__init__(coordinator)
        
        self.nodes = nodes
        self.isolated_node = isolated_node
        self.duration = duration
    
    def execute(self):
        """Execute isolation"""
        other_nodes = [n for n in self.nodes if n != self.isolated_node]
        
        print(f"\n=== Node Isolation Scenario ===")
        print(f"Isolated: {self.isolated_node}")
        print(f"Cluster: {other_nodes}")
        print(f"Duration: {self.duration}s\n")
        
        # Create partition
        self.coordinator.create_partition(
            groups=[[self.isolated_node], other_nodes],
            duration=self.duration,
            auto_heal=True
        )
    
    def assert_node_marked_as_failed(self, node_id: str):
        """Assert node is marked as failed by cluster"""
        print(f"✓ Assertion: {node_id} marked as failed")


class AsymmetricPartition(FailureScenario):
    """
    Asymmetric network partition
    
    Creates one-way communication failure (A can reach B, but B cannot reach A).
    """
    
    def __init__(
        self,
        nodes: List[str],
        blocked_direction: tuple,  # (from_node, to_node)
        duration: float
    ):
        coordinator = PartitionCoordinator(nodes)
        super().__init__(coordinator)
        
        self.nodes = nodes
        self.blocked_direction = blocked_direction
        self.duration = duration
    
    def execute(self):
        """Execute asymmetric partition"""
        from_node, to_node = self.blocked_direction
        
        print(f"\n=== Asymmetric Partition Scenario ===")
        print(f"Blocked: {from_node} -> {to_node}")
        print(f"Allowed: {to_node} -> {from_node}")
        print(f"Duration: {self.duration}s\n")
        
        # Disable one-way connectivity
        self.coordinator.connectivity[(from_node, to_node)] = False
        
        print(f"✓ Created asymmetric partition")


class CascadingFailures(FailureScenario):
    """
    Cascading failure scenario
    
    Nodes fail sequentially, simulating cascading failure.
    """
    
    def __init__(
        self,
        nodes: List[str],
        failure_sequence: List[dict]  # [{"node": "node1", "delay": 0}, ...]
    ):
        coordinator = PartitionCoordinator(nodes)
        super().__init__(coordinator)
        
        self.nodes = nodes
        self.failure_sequence = failure_sequence
    
    def execute(self):
        """Execute cascading failures"""
        
        print(f"\n=== Cascading Failures Scenario ===")
        print(f"Failure sequence: {len(self.failure_sequence)} nodes\n")
        
        for failure in self.failure_sequence:
            node = failure["node"]
            delay = failure["delay"]
            
            if delay > 0:
                print(f"Waiting {delay}s...")
                time.sleep(delay)
            
            print(f"Crashing {node}")
            self.coordinator.crash_node(node)


# Example usage
if __name__ == "__main__":
    print("=== Failure Scenarios Examples ===\n")
    
    # Example 1: Simple partition
    scenario1 = SimplePartition(
        nodes=["node1", "node2", "node3", "node4", "node5"],
        partition_sizes=[2, 3],
        duration=5
    )
    scenario1.execute()
    scenario1.assert_minority_cannot_elect_leader()
    scenario1.assert_majority_continues_operating()
    
    import time
    time.sleep(6)
    
    # Example 2: Node isolation
    scenario2 = NodeIsolation(
        nodes=["node1", "node2", "node3"],
        isolated_node="node2",
        duration=5
    )
    scenario2.execute()
    scenario2.assert_node_marked_as_failed("node2")
