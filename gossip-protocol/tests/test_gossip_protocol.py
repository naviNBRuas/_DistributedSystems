import unittest
import time
import sys
import os
import threading
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from gossip_node import GossipNode, GossipMode
from config import GossipConfig

# Configure logging to show errors during tests
logging.basicConfig(level=logging.ERROR)

class TestGossipProtocol(unittest.TestCase):
    def setUp(self):
        self.nodes = []
        self.base_port = 15000

    def tearDown(self):
        for node in self.nodes:
            node.stop()
        # Allow time for threads to close and sockets to release
        time.sleep(0.5)

    def create_node(self, node_id, port, seeds=None):
        config = GossipConfig(
            gossip_interval=200, # Fast for tests
            gossip_fanout=3,
            phi_threshold=8.0
        )
        node = GossipNode(
            node_id=node_id,
            bind_address=f"127.0.0.1:{port}",
            seed_nodes=seeds or [],
            config=config,
            mode=GossipMode.PUSH_PULL
        )
        self.nodes.append(node)
        return node

    def test_basic_convergence(self):
        """Test that two nodes converge on a single value."""
        # Node 1
        node1 = self.create_node("node1", self.base_port)
        node1.start()

        # Node 2 (seeds with Node 1)
        node2 = self.create_node("node2", self.base_port + 1, seeds=[f"127.0.0.1:{self.base_port}"])
        node2.start()

        # Allow time for membership to settle
        time.sleep(1)

        # Set value on Node 1
        node1.set("test_key", "test_value")

        # Wait for propagation
        time.sleep(2)

        # Check Node 2
        val = node2.get("test_key")
        self.assertEqual(val, "test_value")

    def test_bi_directional_gossip(self):
        """Test that updates propagate both ways."""
        node1 = self.create_node("node1", self.base_port + 2)
        node2 = self.create_node("node2", self.base_port + 3, seeds=[f"127.0.0.1:{self.base_port + 2}"])
        
        node1.start()
        node2.start()
        time.sleep(1)

        node1.set("key1", "val1")
        node2.set("key2", "val2")

        time.sleep(2)

        self.assertEqual(node2.get("key1"), "val1")
        self.assertEqual(node1.get("key2"), "val2")

    def test_multi_node_convergence(self):
        """Test convergence in a 3-node cluster."""
        # A -> B -> C (Chain topology via seeds, but full mesh via gossip)
        node1 = self.create_node("node1", self.base_port + 4)
        node2 = self.create_node("node2", self.base_port + 5, seeds=[f"127.0.0.1:{self.base_port + 4}"])
        node3 = self.create_node("node3", self.base_port + 6, seeds=[f"127.0.0.1:{self.base_port + 5}"])

        for n in self.nodes:
            n.start()
        
        time.sleep(2) # Membership settling

        node1.set("broadcast", "payload")

        time.sleep(3) # Propagation

        self.assertEqual(node2.get("broadcast"), "payload")
        self.assertEqual(node3.get("broadcast"), "payload")

    def test_delete_propagation(self):
        """Test that deletions (tombstones) propagate."""
        node1 = self.create_node("node1", self.base_port + 7)
        node2 = self.create_node("node2", self.base_port + 8, seeds=[f"127.0.0.1:{self.base_port + 7}"])
        
        node1.start()
        node2.start()
        time.sleep(1)

        node1.set("temp", "data")
        time.sleep(1)
        self.assertEqual(node2.get("temp"), "data")

        node1.delete("temp")
        time.sleep(1)
        
        self.assertIsNone(node2.get("temp"))

    def test_subscription(self):
        """Test subscription callbacks."""
        node1 = self.create_node("node1", self.base_port + 9)
        node1.start()

        received = []
        def callback(k, v):
            received.append((k, v))

        node1.subscribe("user:*", callback)
        node1.set("user:123", "alice")

        time.sleep(0.1)
        self.assertEqual(received, [("user:123", "alice")])

if __name__ == '__main__':
    unittest.main()