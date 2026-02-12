"""
Test suite for Consistent Hashing

Tests cover:
- Ring consistency
- Node addition/removal
- Virtual node distribution
- Replication
- Thread safety
- Edge cases
"""

import unittest
import sys
import os
import threading
import time
import random
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from consistent_hash import ConsistentHashRing

# Configure logging to capture output if needed during failed tests
logging.basicConfig(level=logging.INFO)

class TestConsistentHash(unittest.TestCase):
    """Test consistent hashing core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ring = ConsistentHashRing(virtual_nodes=3)
    
    def test_single_node(self):
        """Single node should contain all keys"""
        self.ring.add_node("node_1")
        
        for i in range(10):
            node = self.ring.get_node(f"key_{i}")
            self.assertEqual(node, "node_1")
    
    def test_multiple_nodes_distribution(self):
        """Keys should be distributed across multiple nodes"""
        nodes = ["node_1", "node_2", "node_3"]
        for node in nodes:
            self.ring.add_node(node)
        
        # Each key should map to some node
        keys = [f"key_{i}" for i in range(100)]
        mapped_nodes = set()
        
        for key in keys:
            node = self.ring.get_node(key)
            self.assertIn(node, nodes)
            mapped_nodes.add(node)
        
        # With 100 keys and 3 nodes, it's highly probable all nodes are used
        self.assertEqual(len(mapped_nodes), 3, "Not all nodes were utilized")
    
    def test_minimal_redistribution(self):
        """Adding node should only redistribute a fraction of keys"""
        # Start with 3 nodes
        initial_nodes = ["node_1", "node_2", "node_3"]
        ring = ConsistentHashRing(nodes=initial_nodes, virtual_nodes=50)
        
        keys = [f"key_{i}" for i in range(1000)]
        initial_mapping = {k: ring.get_node(k) for k in keys}
        
        # Add a 4th node
        ring.add_node("node_4")
        new_mapping = {k: ring.get_node(k) for k in keys}
        
        # Check how many keys moved
        moved_keys = 0
        moved_to_new = 0
        
        for k, old_node in initial_mapping.items():
            new_node = new_mapping[k]
            if new_node != old_node:
                moved_keys += 1
                if new_node == "node_4":
                    moved_to_new += 1
        
        # Theoretically, ~1/4 of keys should move. Allow some variance.
        # 1000 keys / 4 nodes = 250 keys per node ideally.
        # So we expect roughly 250 keys to move to node_4.
        
        self.assertGreater(moved_keys, 150, "Too few keys moved")
        self.assertLess(moved_keys, 350, "Too many keys moved")
        
        # Most moved keys should go to the new node (property of consistent hashing)
        # Actually, in consistent hashing, keys ONLY move to the new node (from their successors)
        self.assertEqual(moved_keys, moved_to_new, "Keys moved between existing nodes!")
    
    def test_node_removal_redistribution(self):
        """Removing node should redistribute its keys to others"""
        ring = ConsistentHashRing(nodes=["node_1", "node_2", "node_3"], virtual_nodes=50)
        keys = [f"key_{i}" for i in range(100)]
        
        # Find keys belonging to node_2
        node_2_keys = [k for k in keys if ring.get_node(k) == "node_2"]
        self.assertGreater(len(node_2_keys), 0)
        
        ring.remove_node("node_2")
        
        for k in node_2_keys:
            new_node = ring.get_node(k)
            self.assertNotEqual(new_node, "node_2")
            self.assertIn(new_node, ["node_1", "node_3"])

    def test_get_nodes_replication(self):
        """Test retrieving multiple distinct nodes for replication"""
        ring = ConsistentHashRing(nodes=["n1", "n2", "n3", "n4"], virtual_nodes=10)
        
        key = "resource_abc"
        replicas = ring.get_nodes(key, count=3)
        
        self.assertEqual(len(replicas), 3)
        self.assertEqual(len(set(replicas)), 3, "Replicas must be unique physical nodes")
        
        # Primary node should be the first one
        primary = ring.get_node(key)
        self.assertEqual(replicas[0], primary)
        
        # Requesting more than available
        replicas_all = ring.get_nodes(key, count=10)
        self.assertEqual(len(replicas_all), 4, "Should cap at total physical nodes")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.ring = ConsistentHashRing()
    
    def test_empty_ring(self):
        """Operations on empty ring should be safe"""
        self.assertIsNone(self.ring.get_node("key"))
        self.assertEqual(self.ring.get_nodes("key", 3), [])
        stats = self.ring.get_distribution_stats()
        self.assertEqual(stats, {})
    
    def test_add_duplicate_node(self):
        """Adding existing node should be idempotent"""
        self.ring.add_node("n1")
        v_count_1 = len(self.ring.ring)
        self.ring.add_node("n1")
        v_count_2 = len(self.ring.ring)
        self.assertEqual(v_count_1, v_count_2)
    
    def test_remove_non_existent(self):
        """Removing non-existent node should not crash"""
        self.ring.add_node("n1")
        self.ring.remove_node("n2") # Should log warning but not crash
        self.assertEqual(len(self.ring.nodes), 1)


class TestConcurrency(unittest.TestCase):
    """Test thread safety"""
    
    def test_concurrent_access(self):
        """Concurrent adds/removes/reads should not deadlock or crash"""
        ring = ConsistentHashRing(virtual_nodes=10)
        
        stop_event = threading.Event()
        errors = []
        
        def reader():
            try:
                while not stop_event.is_set():
                    ring.get_node(f"key_{random.randint(0, 1000)}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def writer():
            try:
                nodes = ["n1", "n2", "n3", "n4", "n5"]
                while not stop_event.is_set():
                    action = random.choice(["add", "remove"])
                    node = random.choice(nodes)
                    if action == "add":
                        ring.add_node(node)
                    else:
                        ring.remove_node(node)
                    time.sleep(0.002)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=writer)
        ]
        
        for t in threads:
            t.start()
            
        time.sleep(1) # Run for 1 second
        stop_event.set()
        
        for t in threads:
            t.join()
            
        self.assertEqual(errors, [], f"Concurrency errors occurred: {errors}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
