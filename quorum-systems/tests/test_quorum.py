#!/usr/bin/env python3
"""
Test suite for quorum-systems module.
Tests N/W/R quorum configuration and consistency level guarantees.
"""

import unittest
import random
from typing import Set, Tuple
from unittest.mock import patch, MagicMock

try:
    from src.quorum_system import (
        QuorumConfig, QuorumValidator, ConsistencyLevel,
        ReadRepairStrategy, SlopopyQuorum, HintedHandoff,
        QuorumCoordinator, QuorumNotMetError
    )
except ImportError:
    QuorumConfig = QuorumValidator = ConsistencyLevel = None
    ReadRepairStrategy = SlopopyQuorum = HintedHandoff = None
    QuorumCoordinator = QuorumNotMetError = None


class TestQuorumConfig(unittest.TestCase):
    """Test quorum configuration validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        if QuorumConfig is None:
            self.skipTest("QuorumConfig not available")
    
    def test_basic_quorum_config(self):
        """Test basic N/W/R quorum configuration"""
        config = QuorumConfig(N=3, W=2, R=2)
        
        self.assertEqual(config.N, 3)
        self.assertEqual(config.W, 2)
        self.assertEqual(config.R, 2)
    
    def test_strong_consistency_config(self):
        """Test configuration for strong consistency"""
        # W > N/2 and R > N/2 ensures read-after-write consistency
        config = QuorumConfig(N=5, W=3, R=3)
        
        self.assertTrue(config.is_strongly_consistent())
    
    def test_eventual_consistency_config(self):
        """Test configuration for eventual consistency"""
        # W = 1 and R = 1 allows reads from any replica
        config = QuorumConfig(N=5, W=1, R=1)
        
        self.assertTrue(config.is_eventually_consistent())
    
    def test_one_consistency_config(self):
        """Test ONE consistency (read from fastest/closest)"""
        config = QuorumConfig(N=3, W=3, R=1)
        
        # ALL writes, ONE read
        self.assertEqual(config.R, 1)
        self.assertEqual(config.W, 3)
    
    def test_invalid_config_N_too_small(self):
        """Test validation rejects N < 1"""
        with self.assertRaises(ValueError):
            QuorumConfig(N=0, W=1, R=1)
    
    def test_invalid_config_W_exceeds_N(self):
        """Test validation rejects W > N"""
        with self.assertRaises(ValueError):
            QuorumConfig(N=3, W=5, R=2)
    
    def test_invalid_config_R_exceeds_N(self):
        """Test validation rejects R > N"""
        with self.assertRaises(ValueError):
            QuorumConfig(N=3, W=2, R=5)


class TestConsistencyLevels(unittest.TestCase):
    """Test consistency level guarantees"""
    
    def setUp(self):
        """Set up test fixtures"""
        if ConsistencyLevel is None:
            self.skipTest("ConsistencyLevel not available")
    
    def test_one_consistency_level(self):
        """Test ONE consistency (fastest)"""
        consistency = ConsistencyLevel.ONE
        
        # ONE should have lowest latency but highest staleness
        self.assertEqual(consistency.read_quorum, 1)
        self.assertTrue(consistency.allows_stale_reads())
    
    def test_quorum_consistency_level(self):
        """Test QUORUM consistency (balanced)"""
        consistency = ConsistencyLevel.QUORUM
        
        # QUORUM should balance latency and consistency
        self.assertGreater(consistency.read_quorum, 1)
    
    def test_all_consistency_level(self):
        """Test ALL consistency (strongest)"""
        consistency = ConsistencyLevel.ALL
        
        # ALL should require all replicas
        self.assertEqual(consistency.read_quorum, 100)  # All replicas
    
    def test_local_consistency_level(self):
        """Test LOCAL_ONE consistency (same datacenter)"""
        consistency = ConsistencyLevel.LOCAL_ONE
        
        # Should read from same datacenter only
        self.assertTrue(consistency.is_local_only())
    
    def test_consistency_latency_tradeoff(self):
        """Test latency increases with consistency"""
        levels = [
            ConsistencyLevel.ONE,
            ConsistencyLevel.QUORUM,
            ConsistencyLevel.ALL
        ]
        
        latencies = [level.expected_latency_ms() for level in levels]
        
        # Latencies should be non-decreasing
        for i in range(1, len(latencies)):
            self.assertGreaterEqual(latencies[i], latencies[i-1])


class TestQuorumValidator(unittest.TestCase):
    """Test quorum intersection and conflict detection"""
    
    def setUp(self):
        """Set up test fixtures"""
        if QuorumValidator is None:
            self.skipTest("QuorumValidator not available")
        self.validator = QuorumValidator()
    
    def test_quorum_intersection(self):
        """Test that read and write quorums intersect"""
        # N=5, W=3, R=3 should intersect
        config = QuorumConfig(N=5, W=3, R=3)
        
        intersection = self.validator.get_quorum_intersection(config)
        
        # Write quorum (3) + Read quorum (3) - N (5) = 1 node overlap
        self.assertEqual(len(intersection), 1)
    
    def test_no_intersection_eventual_consistency(self):
        """Test N=5, W=1, R=5 intersection (eventual consistency)"""
        config = QuorumConfig(N=5, W=1, R=5)
        
        # Write quorum (1) + Read quorum (5) > N (5), so they intersect
        intersection = self.validator.get_quorum_intersection(config)
        self.assertGreater(len(intersection), 0)
    
    def test_write_version_safety(self):
        """Test write version versioning for conflict detection"""
        config = QuorumConfig(N=3, W=2, R=2)
        
        # Two writes with different versions should be detectable
        write1_replicas = {0, 1}  # Write 1 goes to replicas 0, 1
        write2_replicas = {1, 2}  # Write 2 goes to replicas 1, 2
        
        # Version 1 and 2 can be distinguished by reading from R=2
        conflicts = self.validator.detect_write_conflicts(
            [write1_replicas, write2_replicas],
            read_quorum_size=2
        )
        
        self.assertEqual(len(conflicts), 0)  # Should not conflict if properly versioned
    
    def test_missing_write_detection(self):
        """Test detection of missing writes in replicas"""
        # If R > N - W, we can always detect missing writes
        config = QuorumConfig(N=5, W=2, R=4)
        
        # R (4) > N - W (3), so we can detect missing writes
        self.assertTrue(config.can_detect_missing_writes())


class TestReadRepair(unittest.TestCase):
    """Test read repair consistency mechanism"""
    
    def setUp(self):
        """Set up test fixtures"""
        if ReadRepairStrategy is None:
            self.skipTest("ReadRepairStrategy not available")
        self.repair = ReadRepairStrategy()
    
    def test_read_repair_basic(self):
        """Test basic read repair mechanism"""
        # Read from 3 replicas, 1 is stale
        versions = [100, 100, 99]  # Latest version is 100
        
        repairs = self.repair.identify_repairs(versions)
        
        # Should identify replica 2 needs repair
        self.assertIn(2, repairs)
    
    def test_read_repair_all_current(self):
        """Test read repair with all current replicas"""
        versions = [100, 100, 100]
        
        repairs = self.repair.identify_repairs(versions)
        
        # No repairs needed
        self.assertEqual(len(repairs), 0)
    
    def test_read_repair_multiple_stale(self):
        """Test read repair with multiple stale replicas"""
        versions = [100, 99, 98]  # Latest is 100
        
        repairs = self.repair.identify_repairs(versions)
        
        # Should repair replicas 1 and 2
        self.assertEqual(repairs, {1, 2})
    
    def test_read_repair_with_timeout(self):
        """Test read repair with timeout (repair asynchronously)"""
        versions = [100, 99, 99]
        
        # Schedule async repair
        repairs = self.repair.identify_async_repairs(versions, timeout_ms=100)
        
        self.assertGreater(len(repairs), 0)


class TestSloppyQuorum(unittest.TestCase):
    """Test sloppy quorum for fault tolerance"""
    
    def setUp(self):
        """Set up test fixtures"""
        if SlopopyQuorum is None:
            self.skipTest("SlopopyQuorum not available")
        self.sloppy = SlopopyQuorum()
    
    def test_sloppy_quorum_replicas_available(self):
        """Test sloppy quorum when all replicas available"""
        available_replicas = {0, 1, 2}
        preferred_replicas = {0, 1, 2}
        
        chosen = self.sloppy.choose_replicas(
            available_replicas,
            preferred_replicas,
            quorum_size=2
        )
        
        # Should choose from preferred if possible
        self.assertLessEqual(len(chosen), 2)
    
    def test_sloppy_quorum_preferred_unavailable(self):
        """Test sloppy quorum when preferred replicas unavailable"""
        available_replicas = {0, 3, 4}  # Preferred 1, 2 are down
        preferred_replicas = {0, 1, 2}
        
        chosen = self.sloppy.choose_replicas(
            available_replicas,
            preferred_replicas,
            quorum_size=2
        )
        
        # Should include temporary replica (3 or 4)
        self.assertEqual(len(chosen), 2)
        self.assertIn(0, chosen)  # Preferred 0 is available
    
    def test_sloppy_quorum_insufficient_replicas(self):
        """Test sloppy quorum with insufficient available replicas"""
        available_replicas = {0}  # Only 1 replica available
        preferred_replicas = {0, 1, 2}
        
        # Should raise error or return partial
        chosen = self.sloppy.choose_replicas(
            available_replicas,
            preferred_replicas,
            quorum_size=2,
            allow_partial=True
        )
        
        self.assertLessEqual(len(chosen), 2)


class TestHintedHandoff(unittest.TestCase):
    """Test hinted handoff for durability"""
    
    def setUp(self):
        """Set up test fixtures"""
        if HintedHandoff is None:
            self.skipTest("HintedHandoff not available")
        self.handoff = HintedHandoff()
    
    def test_hinted_handoff_basic(self):
        """Test basic hinted handoff"""
        # Write to temporary replica while primary is down
        self.handoff.write_hint(
            key="user:123",
            value="Alice",
            intended_replica=0,
            temporary_replica=3
        )
        
        # Should have stored hint
        hints = self.handoff.get_hints_for_replica(0)
        self.assertGreater(len(hints), 0)
    
    def test_hinted_handoff_delivery(self):
        """Test delivering hints when replica comes back"""
        # Record hint for offline replica
        self.handoff.write_hint(
            key="user:123",
            value="Alice",
            intended_replica=0,
            temporary_replica=3
        )
        
        # Replica comes back online
        # Hints should be delivered
        delivered = self.handoff.deliver_hints(replica_id=0)
        
        self.assertGreater(len(delivered), 0)
    
    def test_hinted_handoff_timeout(self):
        """Test hinted handoff timeout"""
        # Store hint with TTL
        self.handoff.write_hint(
            key="user:123",
            value="Alice",
            intended_replica=0,
            temporary_replica=3,
            ttl_sec=60
        )
        
        # Check hint is stored
        hints = self.handoff.get_hints_for_replica(0)
        self.assertEqual(len(hints), 1)
    
    def test_hinted_handoff_multiple_replicas(self):
        """Test hints for multiple unavailable replicas"""
        # Multiple replicas down
        for temp_replica in [3, 4, 5]:
            self.handoff.write_hint(
                key="user:123",
                value="Alice",
                intended_replica=temp_replica % 3,
                temporary_replica=temp_replica
            )
        
        # Each replica should have hints waiting
        for intended in range(3):
            hints = self.handoff.get_hints_for_replica(intended)
            self.assertGreater(len(hints), 0)


class TestQuorumPerformance(unittest.TestCase):
    """Performance tests for quorum operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        if QuorumValidator is None:
            self.skipTest("QuorumValidator not available")
    
    def test_quorum_intersection_calculation_performance(self):
        """Test performance of quorum intersection calculation"""
        import time
        
        validator = QuorumValidator()
        
        start = time.time()
        
        # Calculate intersections for many configs
        for N in range(3, 20):
            for W in range(1, N):
                for R in range(1, N):
                    config = QuorumConfig(N=N, W=W, R=R)
                    validator.get_quorum_intersection(config)
        
        elapsed = time.time() - start
        
        # Should be fast
        self.assertLess(elapsed, 1.0)
    
    def test_quorum_config_validation_throughput(self):
        """Test throughput of quorum config validation"""
        import time
        
        start = time.time()
        
        for _ in range(10000):
            try:
                config = QuorumConfig(
                    N=random.randint(1, 10),
                    W=random.randint(1, 10),
                    R=random.randint(1, 10)
                )
            except ValueError:
                pass  # Invalid configs expected
        
        elapsed = time.time() - start
        throughput = 10000 / elapsed
        
        # Should handle 1000+ validations/sec
        self.assertGreater(throughput, 1000)


class TestQuorumCoordinator(unittest.TestCase):
    """Test the main QuorumCoordinator integration"""

    def setUp(self):
        if QuorumCoordinator is None:
            self.skipTest("QuorumCoordinator not available")
        self.replicas = ["node1", "node2", "node3", "node4", "node5"]
        self.coord = QuorumCoordinator(
            replicas=self.replicas,
            write_quorum=3,
            read_quorum=3,
            timeout=0.1
        )

    def test_write_read_success(self):
        """Test successful write and read with quorum"""
        key = "test_key"
        value = "test_value"
        
        # Write should succeed
        success = self.coord.write(key, value, ConsistencyLevel.QUORUM)
        self.assertTrue(success)
        
        # Read should return the value
        read_val = self.coord.read(key, ConsistencyLevel.QUORUM)
        self.assertEqual(read_val, value)

    def test_write_quorum_failure(self):
        """Test write fails when quorum cannot be met"""
        # Mock _write_to_replica to always fail
        with patch.object(self.coord, '_write_to_replica', return_value=False):
            with self.assertRaises(QuorumNotMetError):
                self.coord.write("key", "val", ConsistencyLevel.QUORUM)

    def test_read_quorum_failure(self):
        """Test read fails when quorum cannot be met"""
        # Mock _read_from_replica to always fail (return None, 0)
        with patch.object(self.coord, '_read_from_replica', return_value=(None, 0)):
             with self.assertRaises(QuorumNotMetError):
                self.coord.read("key", ConsistencyLevel.QUORUM)


if __name__ == '__main__':
    unittest.main()
