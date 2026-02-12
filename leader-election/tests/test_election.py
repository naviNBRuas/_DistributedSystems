"""
Test suite for Leader Election implementations

Tests cover:
- Election under various network conditions
- Fencing token generation
- Handling of concurrent candidates
- Split-brain prevention
"""

import unittest
import time
import logging
import sys
import os
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from bully_algorithm import BullyElection
from election_manager import ElectionManager, Algorithm
from fencing import FencingTokenManager
from local_transport import LocalTransport, LocalNetwork

# Configure logging for tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class TestBullyAlgorithm(unittest.TestCase):
    """Test Bully algorithm with LocalTransport"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Reset local network
        LocalNetwork._instance = None
        self.nodes = []
    
    def tearDown(self):
        """Clean up"""
        for node in self.nodes:
            node.stop()
    
    def create_node(self, node_id, peers):
        transport = LocalTransport(node_id)
        manager = ElectionManager(
            node_id=node_id,
            peers=peers,
            transport=transport,
            algorithm=Algorithm.BULLY,
            election_timeout=1.0,
            heartbeat_interval=0.2
        )
        self.nodes.append(manager)
        return manager
    
    def test_higher_id_wins_integration(self):
        """Node with higher ID should win in a 3-node cluster"""
        peers = ["node_1", "node_2", "node_3"]
        
        n1 = self.create_node("node_1", ["node_2", "node_3"])
        n2 = self.create_node("node_2", ["node_1", "node_3"])
        n3 = self.create_node("node_3", ["node_1", "node_2"])
        
        n1.start()
        n2.start()
        n3.start()
        
        # Give time for election
        time.sleep(2.5)
        
        # Node 3 should be leader
        self.assertTrue(n3.is_leader(), "Node 3 should be leader")
        self.assertFalse(n2.is_leader(), "Node 2 should not be leader")
        self.assertFalse(n1.is_leader(), "Node 1 should not be leader")
        
        self.assertEqual(n1.get_leader(), "node_3")
        self.assertEqual(n2.get_leader(), "node_3")

    def test_failover(self):
        """If leader dies, next highest should take over"""
        n1 = self.create_node("node_1", ["node_2", "node_3"])
        n2 = self.create_node("node_2", ["node_1", "node_3"])
        n3 = self.create_node("node_3", ["node_1", "node_2"])
        
        n1.start()
        n2.start()
        n3.start()
        
        time.sleep(2.0)
        self.assertEqual(n1.get_leader(), "node_3")
        
        # Kill node 3
        print("Stopping Node 3")
        n3.stop()
        
        # Wait for timeout and new election
        time.sleep(3.0)
        
        # Node 2 should be leader now
        self.assertTrue(n2.is_leader(), "Node 2 should take over")
        self.assertEqual(n1.get_leader(), "node_2")


class TestRingAlgorithm(unittest.TestCase):
    """Test Ring algorithm"""
    
    def setUp(self):
        LocalNetwork._instance = None
        self.nodes = []

    def tearDown(self):
        for node in self.nodes:
            node.stop()

    def create_node(self, node_id, peers):
        transport = LocalTransport(node_id)
        manager = ElectionManager(
            node_id=node_id,
            peers=peers,
            transport=transport,
            algorithm=Algorithm.RING,
            election_timeout=1.0
        )
        self.nodes.append(manager)
        return manager

    def test_ring_election(self):
        n1 = self.create_node("node_1", ["node_2", "node_3"])
        n2 = self.create_node("node_2", ["node_1", "node_3"])
        n3 = self.create_node("node_3", ["node_1", "node_2"])
        
        n1.start()
        n2.start()
        n3.start()
        
        time.sleep(2.0)
        
        # Highest ID (node_3) should win
        self.assertEqual(n1.get_leader(), "node_3")
        self.assertEqual(n2.get_leader(), "node_3")
        self.assertEqual(n3.get_leader(), "node_3")


class TestLeaseAlgorithm(unittest.TestCase):
    """Test Lease/Quorum algorithm"""
    
    def setUp(self):
        LocalNetwork._instance = None
        self.nodes = []

    def tearDown(self):
        for node in self.nodes:
            node.stop()

    def create_node(self, node_id, peers):
        transport = LocalTransport(node_id)
        manager = ElectionManager(
            node_id=node_id,
            peers=peers,
            transport=transport,
            algorithm=Algorithm.LEASE,
            lease_duration=2.0,
            renew_interval=0.5
        )
        self.nodes.append(manager)
        return manager

    def test_lease_acquisition(self):
        n1 = self.create_node("node_1", ["node_2", "node_3"])
        n2 = self.create_node("node_2", ["node_1", "node_3"])
        n3 = self.create_node("node_3", ["node_1", "node_2"])
        
        n1.start()
        n2.start()
        n3.start()
        
        time.sleep(3.0)
        
        # Someone should have acquired the lease.
        # It's random backoff, so anyone could win, but they should agree.
        l1 = n1.get_leader()
        l2 = n2.get_leader()
        l3 = n3.get_leader()
        
        self.assertIsNotNone(l1)
        self.assertEqual(l1, l2)
        self.assertEqual(l2, l3)
        
        print(f"Lease winner: {l1}")


class TestFencingTokens(unittest.TestCase):
    """Test fencing token mechanism"""
    
    def setUp(self):
        self.manager = FencingTokenManager()
    
    def test_monotonic_tokens(self):
        token1 = self.manager.issue_token("node_1")
        token2 = self.manager.issue_token("node_1")
        
        self.assertLess(token1.epoch, token2.epoch)
    
    def test_token_validation(self):
        token1 = self.manager.issue_token("node_1")
        self.assertTrue(self.manager.validate_token(token1))
        
        token2 = self.manager.issue_token("node_2")
        self.assertFalse(self.manager.validate_token(token1), "Old token should be invalid")
        self.assertTrue(self.manager.validate_token(token2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
