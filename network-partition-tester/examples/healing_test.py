"""
Example: Healing Test

Demonstrates various strategies for partition recovery and healing.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from partition_coordinator import PartitionCoordinator


class HealingTest:
    def __init__(self):
        self.nodes = ["node1", "node2", "node3", "node4"]
        self.coordinator = PartitionCoordinator(self.nodes)
        
    def test_auto_heal(self):
        """Test automatic healing after duration"""
        print("\n=== Test: Automatic Healing ===")
        
        duration = 3
        print(f"Creating partition with {duration}s duration...")
        
        self.coordinator.create_partition(
            groups=[["node1", "node2"], ["node3", "node4"]],
            duration=duration,
            auto_heal=True
        )
        
        print("Waiting...")
        time.sleep(duration + 1.5)  # Wait for duration + buffer
        
        # Verify healed
        active = self.coordinator.get_active_partitions()
        if not active:
            print("✓ Partition automatically healed")
        else:
            print("✗ Partition failed to heal")
            
    def test_manual_heal(self):
        """Test manual healing of specific partition"""
        print("\n=== Test: Manual Healing ===")
        
        pid = self.coordinator.create_partition(
            groups=[["node1"], ["node2", "node3", "node4"]],
            duration=None,
            auto_heal=False
        )
        print(f"Created permanent partition: {pid}")
        
        # Verify active
        assert len(self.coordinator.get_active_partitions()) == 1
        
        print("Manually healing...")
        self.coordinator.heal_partition(pid)
        
        # Verify healed
        if not self.coordinator.get_active_partitions():
            print("✓ Partition manually healed")
        else:
            print("✗ Partition failed to heal")
            
    def test_gradual_recovery(self):
        """
        Test recovering nodes one by one (Gradual Healing). 
        
        Note: The current Coordinator implementation heals partitions atomically.
        This test simulates gradual healing by updating the partition configuration.
        """
        print("\n=== Test: Gradual Recovery ===")
        
        # Start with full split
        # Group A: [1, 2], Group B: [3, 4]
        print("Phase 1: Full Split [1,2] | [3,4]")
        self.coordinator.create_partition(
            groups=[["node1", "node2"], ["node3", "node4"]],
            duration=None
        )
        
        time.sleep(1)
        self.coordinator.heal_partition() # Reset for next phase
        
        # Move node3 to Group A
        # Group A: [1, 2, 3], Group B: [4]
        print("Phase 2: Partial Merge [1,2,3] | [4]")
        self.coordinator.create_partition(
            groups=[["node1", "node2", "node3"], ["node4"]],
            duration=None
        )
        
        # Verify connectivity
        if self.coordinator.can_communicate("node1", "node3"):
            print("✓ node1 can reach node3 (merged)")
        if not self.coordinator.can_communicate("node1", "node4"):
            print("✓ node1 cannot reach node4 (still isolated)")
            
        time.sleep(1)
        
        # Full heal
        print("Phase 3: Full Heal")
        self.coordinator.heal_partition()
        
        if self.coordinator.can_communicate("node1", "node4"):
            print("✓ Full connectivity restored")

    def cleanup(self):
        self.coordinator.cleanup()


if __name__ == "__main__":
    test = HealingTest()
    try:
        test.test_auto_heal()
        test.test_manual_heal()
        test.test_gradual_recovery()
    finally:
        test.cleanup()
