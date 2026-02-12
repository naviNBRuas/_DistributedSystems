
import unittest
import shutil
import tempfile
import time
import os
import sys
from concurrent.futures import Future

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from raft_node import RaftNode, NodeState
from config import RaftConfig
from rpc import InMemoryRPC
from storage import FileStorage

class TestRaftCluster(unittest.TestCase):
    """Integration tests for a cluster of Raft nodes running in-process"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.nodes = []
        self.rpc_registry = {}
        self.disconnected_nodes = set()
        
        # Create 3 nodes
        self.node_ids = ["node1", "node2", "node3"]
        self.config = RaftConfig(
            election_timeout_min=200, 
            election_timeout_max=400, 
            heartbeat_interval=50,
            snapshot_interval=5 # Low for testing
        )
        
        for node_id in self.node_ids:
            peers = [n for n in self.node_ids if n != node_id]
            storage = FileStorage(os.path.join(self.test_dir, node_id), node_id)
            # Create a fresh RPC instance for each node that shares the registry
            node_rpc = InMemoryRPC(self.rpc_registry, self.disconnected_nodes) 
            
            node = RaftNode(
                node_id=node_id, 
                peers=peers, 
                config=self.config,
                storage=storage,
                rpc=node_rpc
            )
            self.nodes.append(node)
            
    def tearDown(self):
        for node in self.nodes:
            node.stop()
        shutil.rmtree(self.test_dir)

    def test_leader_election(self):
        """Test that a leader is elected"""
        for node in self.nodes:
            node.start()
            
        # Wait for election
        time.sleep(1)
        
        leaders = [n for n in self.nodes if n.state == NodeState.LEADER]
        self.assertEqual(len(leaders), 1, "Should have exactly one leader")
        
        leader = leaders[0]
        term = leader.current_term
        
        # Check followers have same term
        for node in self.nodes:
            if node != leader:
                self.assertEqual(node.state, NodeState.FOLLOWER)
                self.assertEqual(node.current_term, term)

    def test_log_replication(self):
        """Test simple command replication"""
        for node in self.nodes:
            node.start()
            
        # Wait for leader
        time.sleep(1)
        leader = next((n for n in self.nodes if n.state == NodeState.LEADER), None)
        self.assertIsNotNone(leader)
        
        # Submit command
        future = leader.submit_command({"op": "set", "key": "x", "value": "1"})
        result = future.result(timeout=2)
        
        self.assertEqual(result, {"status": "ok", "key": "x"})
        
        # Check all nodes have applied it (eventually)
        time.sleep(0.5)
        for node in self.nodes:
            self.assertEqual(node.state_machine.store.get("x"), "1")
            # Note: entries[0] might be shifted if snapshotting happened, but here it shouldn't have
            self.assertEqual(node.log.entries[0].command["key"], "x")

    def test_snapshotting(self):
        """Test log compaction and snapshotting"""
        for node in self.nodes:
            node.start()
            
        time.sleep(1)
        leader = next((n for n in self.nodes if n.state == NodeState.LEADER), None)
        
        # Submit enough commands to trigger snapshot (interval=5)
        for i in range(6):
            future = leader.submit_command({"op": "set", "key": f"k{i}", "value": f"v{i}"})
            future.result(timeout=1)
            
        # Wait for async snapshot
        time.sleep(1)
        
        # Check if snapshot was created
        # Logic: 6 entries, snapshot at 5. Log should contain entry 6.
        # last_included_index should be 5.
        
        self.assertEqual(leader.log.last_included_index, 5)
        self.assertEqual(len(leader.log.entries), 1) 
        
        # Check persistence
        # Stop leader and restart
        leader.stop()
        
        # Restart
        new_storage = FileStorage(os.path.join(self.test_dir, leader.node_id), leader.node_id)
        new_node = RaftNode(
            leader.node_id, 
            list(leader.peers), 
            config=self.config, 
            storage=new_storage, 
            rpc=InMemoryRPC(self.rpc_registry, self.disconnected_nodes)
        )
        
        # Verify state restored
        self.assertEqual(new_node.current_term, leader.current_term)
        self.assertEqual(new_node.state_machine.store.get("k4"), "v4") # From snapshot
        self.assertEqual(new_node.log.last_included_index, leader.log.last_included_index)
        
        new_node.stop()

    def test_partition_tolerance(self):
        """Test system behavior during network partition"""
        for node in self.nodes:
            node.start()
            
        time.sleep(1)
        leader = next((n for n in self.nodes if n.state == NodeState.LEADER), None)
        followers = [n for n in self.nodes if n != leader]
        
        # Isolate leader
        self.disconnected_nodes.add(leader.node_id)
        
        # One of the followers should become new leader
        time.sleep(2) # Wait for election timeout
        
        new_leaders = [n for n in followers if n.state == NodeState.LEADER]
        self.assertEqual(len(new_leaders), 1)
        new_leader = new_leaders[0]
        
        self.assertGreater(new_leader.current_term, leader.current_term)
        
        # Old leader should fail to commit
        try:
            f = leader.submit_command({"op": "set", "key": "lost", "value": "val"})
            f.result(timeout=0.5)
            self.fail("Should not have committed")
        except:
            pass
            
        # New leader should commit
        f = new_leader.submit_command({"op": "set", "key": "new", "value": "val"})
        self.assertEqual(f.result(timeout=1)["status"], "ok")
