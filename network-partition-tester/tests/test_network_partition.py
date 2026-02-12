#!/usr/bin/env python3
"""
Test suite for network-partition-tester module.
Tests controlled network fault injection and failure scenarios.
"""

import unittest
import time
import threading
from src.partition_coordinator import PartitionCoordinator
from src.latency_injector import LatencyInjector
from src.packet_dropper import PacketDropper
from src.failure_scenarios import SimplePartition, NodeIsolation
from src.network_proxy import NetworkProxy
from src.assertions import ClusterAssertions
from src.recorder import ScenarioRecorder, ScenarioReplayer

class TestPartitionCoordinator(unittest.TestCase):
    """Test partition coordinator functionality"""
    
    def setUp(self):
        self.nodes = ["node1", "node2", "node3", "node4", "node5"]
        self.coordinator = PartitionCoordinator(self.nodes)
        
    def tearDown(self):
        self.coordinator.cleanup()
        
    def test_create_partition(self):
        """Test creating a network partition"""
        groups = [["node1", "node2"], ["node3", "node4", "node5"]]
        self.coordinator.create_partition(groups)
        
        # Nodes within group should communicate
        self.assertTrue(self.coordinator.can_communicate("node1", "node2"))
        self.assertTrue(self.coordinator.can_communicate("node3", "node4"))
        
        # Nodes across groups should not communicate
        self.assertFalse(self.coordinator.can_communicate("node1", "node3"))
        self.assertFalse(self.coordinator.can_communicate("node2", "node5"))
        
    def test_heal_partition(self):
        """Test healing a partition"""
        groups = [["node1"], ["node2", "node3", "node4", "node5"]]
        pid = self.coordinator.create_partition(groups)
        
        self.assertFalse(self.coordinator.can_communicate("node1", "node2"))
        
        self.coordinator.heal_partition(pid)
        self.assertTrue(self.coordinator.can_communicate("node1", "node2"))
        
    def test_crash_node(self):
        """Test node crash simulation"""
        self.coordinator.crash_node("node1")
        
        # Crashed node shouldn't communicate with anyone
        self.assertFalse(self.coordinator.can_communicate("node1", "node2"))
        self.assertFalse(self.coordinator.can_communicate("node2", "node1"))
        
        self.coordinator.recover_node("node1")
        self.assertTrue(self.coordinator.can_communicate("node1", "node2"))


class TestLatencyInjector(unittest.TestCase):
    """Test latency injection"""
    
    def setUp(self):
        self.injector = LatencyInjector()
        
    def test_latency_delay(self):
        """Test that latency adds delay"""
        self.injector.add_latency("node1", "node2", latency_ms=100)
        
        start = time.time()
        self.injector.delay_message("node1", "node2")
        elapsed = time.time() - start
        
        # Should be at least 100ms (allow small margin for execution time)
        self.assertGreaterEqual(elapsed, 0.1)
        
    def test_variable_latency(self):
        """Test variable latency function"""
        self.injector.add_latency(
            "node1", "node2",
            latency_fn=lambda size: size / 1000  # 1ms per byte for test simplicity
        )
        
        latency_small = self.injector.get_latency("node1", "node2", 10)
        latency_large = self.injector.get_latency("node1", "node2", 100)
        
        self.assertLess(latency_small, latency_large)


class TestPacketDropper(unittest.TestCase):
    """Test packet loss simulation"""
    
    def setUp(self):
        self.dropper = PacketDropper()
        
    def test_packet_loss(self):
        """Test basic packet loss probability"""
        self.dropper.set_loss_rate("node1", "node2", 1.0)  # 100% loss
        self.assertTrue(self.dropper.should_drop("node1", "node2"))
        
        self.dropper.set_loss_rate("node1", "node2", 0.0)  # 0% loss
        self.assertFalse(self.dropper.should_drop("node1", "node2"))
        
    def test_conditional_drop(self):
        """Test conditional dropping"""
        self.dropper.drop_if(lambda msg: msg == "DROP", 1.0)
        
        self.assertTrue(self.dropper.should_drop("n1", "n2", "DROP"))
        self.assertFalse(self.dropper.should_drop("n1", "n2", "KEEP"))


class TestNetworkProxy(unittest.TestCase):
    """Test network proxy integration"""
    
    def setUp(self):
        self.coordinator = PartitionCoordinator(["node1", "node2"])
        self.proxy = NetworkProxy(self.coordinator)
        
    def tearDown(self):
        self.coordinator.cleanup()
        
    def test_proxy_integration(self):
        """Test that proxy respects coordinator state"""
        self.assertTrue(self.proxy.send("node1", "node2"))
        
        self.coordinator.create_partition([["node1"], ["node2"]])
        self.assertFalse(self.proxy.send("node1", "node2"))
        
        self.coordinator.heal_partition()
        self.assertTrue(self.proxy.send("node1", "node2"))


class TestRecorder(unittest.TestCase):
    """Test scenario recording and replay"""
    
    def setUp(self):
        self.recorder = ScenarioRecorder()
        self.coordinator = PartitionCoordinator(["node1", "node2"])
        self.replayer = ScenarioReplayer(self.coordinator)
        
    def tearDown(self):
        self.coordinator.cleanup()
        
    def test_record_replay(self):
        """Test recording and replaying events"""
        import tempfile
        import os
        
        # Record
        self.recorder.start("test")
        self.recorder.record("create_partition", groups=[["node1"], ["node2"]])
        self.recorder.stop()
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            temp_path = f.name
            
        try:
            self.recorder.save(temp_path)
            
            # Replay
            self.replayer.load(temp_path)
            self.replayer.replay()
            
            # Check effect
            self.assertFalse(self.coordinator.can_communicate("node1", "node2"))
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()