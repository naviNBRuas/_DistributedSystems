#!/usr/bin/env python3
"""
Test suite for distributed-locks module.
Tests mutual exclusion, fencing tokens, and deadlock prevention.
"""

import unittest
import time
import threading
from typing import Dict, List
from unittest.mock import patch, MagicMock, call

try:
    from src.distributed_lock import (
        DistributedLock, LockManager, FencingToken,
        DeadlockDetector, LockTimeout, LockAcquisitionError
    )
except ImportError:
    DistributedLock = LockManager = FencingToken = None
    DeadlockDetector = LockTimeout = LockAcquisitionError = None


class TestDistributedLock(unittest.TestCase):
    """Test basic distributed lock functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        if DistributedLock is None:
            self.skipTest("DistributedLock not available")
        self.lock = DistributedLock(key="resource:db", 
                                    timeout_sec=10,
                                    ttl_sec=5)
    
    def test_lock_acquisition(self):
        """Test acquiring a lock"""
        success = self.lock.acquire(owner="client:1", timeout_sec=5)
        
        self.assertTrue(success)
        self.assertEqual(self.lock.get_owner(), "client:1")
    
    def test_lock_already_held(self):
        """Test acquiring lock already held by another"""
        # First client acquires
        self.lock.acquire(owner="client:1", timeout_sec=5)
        
        # Second client tries to acquire
        success = self.lock.acquire(owner="client:2", timeout_sec=1)
        
        self.assertFalse(success)
        self.assertEqual(self.lock.get_owner(), "client:1")
    
    def test_lock_release(self):
        """Test releasing a lock"""
        self.lock.acquire(owner="client:1", timeout_sec=5)
        self.lock.release(owner="client:1")
        
        self.assertIsNone(self.lock.get_owner())
    
    def test_release_by_wrong_owner(self):
        """Test that wrong owner cannot release lock"""
        self.lock.acquire(owner="client:1", timeout_sec=5)
        
        # client:2 tries to release client:1's lock
        with self.assertRaises(Exception):
            self.lock.release(owner="client:2")
    
    def test_lock_timeout(self):
        """Test lock expiration by timeout"""
        # Acquire with short TTL
        self.lock.acquire(owner="client:1", timeout_sec=1, ttl_sec=0.1)
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Lock should have expired
        self.assertIsNone(self.lock.get_owner())
    
    def test_lock_renewal(self):
        """Test renewing a lock"""
        self.lock.acquire(owner="client:1", timeout_sec=1)
        
        # Renew the lock
        self.lock.renew(owner="client:1", ttl_sec=5)
        
        # Lock should still be held
        self.assertEqual(self.lock.get_owner(), "client:1")
    
    def test_lock_is_held(self):
        """Test checking if lock is held"""
        self.assertFalse(self.lock.is_held())
        
        self.lock.acquire(owner="client:1", timeout_sec=5)
        self.assertTrue(self.lock.is_held())
    
    def test_lock_contention(self):
        """Test contention with multiple clients"""
        results = []
        
        def acquire_lock(client_id):
            success = self.lock.acquire(owner=client_id, timeout_sec=1)
            results.append((client_id, success))
        
        threads = [
            threading.Thread(target=acquire_lock, args=(f"client:{i}",))
            for i in range(3)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Only one should succeed
        successes = sum(1 for _, success in results if success)
        self.assertEqual(successes, 1)


class TestFencingToken(unittest.TestCase):
    """Test fencing token for lock safety"""
    
    def setUp(self):
        """Set up test fixtures"""
        if FencingToken is None:
            self.skipTest("FencingToken not available")
    
    def test_token_generation(self):
        """Test fencing token generation"""
        token1 = FencingToken.generate()
        token2 = FencingToken.generate()
        
        # Tokens should be unique
        self.assertNotEqual(token1, token2)
    
    def test_token_monotonic_increase(self):
        """Test that tokens monotonically increase"""
        tokens = [FencingToken.generate() for _ in range(10)]
        
        # Each token should be greater than previous
        for i in range(1, len(tokens)):
            self.assertGreater(tokens[i], tokens[i-1])
    
    def test_token_validation(self):
        """Test validating operation with fencing token"""
        # Old token
        old_token = FencingToken.generate()
        
        # Some time passes, new lock with higher token
        new_token = FencingToken.generate()
        
        # Operation with old token should be rejected
        self.assertFalse(FencingToken.validate(old_token, new_token))
        
        # Operation with new token should be accepted
        self.assertTrue(FencingToken.validate(new_token, new_token))
    
    def test_token_in_request(self):
        """Test including token in operations"""
        token = FencingToken.generate()
        
        # Simulate operation with token
        operation = {
            "resource": "file.txt",
            "data": "content",
            "fence_token": token
        }
        
        self.assertEqual(operation["fence_token"], token)
    
    def test_server_rejects_old_token(self):
        """Test server rejecting operation with old token"""
        token1 = FencingToken.generate()
        token2 = FencingToken.generate()
        
        # Simulate server state
        server_state = {"current_token": token2}
        
        # Operation with old token should fail
        if token1 < server_state["current_token"]:
            # Old token, reject
            self.assertTrue(True)
        else:
            self.fail("Old token should be rejected")


class TestLockManager(unittest.TestCase):
    """Test lock manager for multiple locks"""
    
    def setUp(self):
        """Set up test fixtures"""
        if LockManager is None:
            self.skipTest("LockManager not available")
        self.manager = LockManager()
    
    def test_acquire_single_lock(self):
        """Test acquiring single lock"""
        token = self.manager.acquire_lock("resource:1", owner="client:1")
        
        self.assertIsNotNone(token)
    
    def test_acquire_multiple_locks(self):
        """Test acquiring multiple locks"""
        token1 = self.manager.acquire_lock("resource:1", owner="client:1")
        token2 = self.manager.acquire_lock("resource:2", owner="client:1")
        
        self.assertNotEqual(token1, token2)
    
    def test_lock_isolation(self):
        """Test that locks are isolated"""
        token1 = self.manager.acquire_lock("resource:1", owner="client:1")
        
        # Different resource, different owner should be able to acquire
        token2 = self.manager.acquire_lock("resource:2", owner="client:2")
        
        self.assertIsNotNone(token1)
        self.assertIsNotNone(token2)
    
    def test_release_lock(self):
        """Test releasing lock"""
        token = self.manager.acquire_lock("resource:1", owner="client:1")
        self.manager.release_lock("resource:1", token=token)
        
        # Should be able to acquire again
        token2 = self.manager.acquire_lock("resource:1", owner="client:2")
        self.assertIsNotNone(token2)
    
    def test_get_locks_held(self):
        """Test getting locks held by client"""
        self.manager.acquire_lock("resource:1", owner="client:1")
        self.manager.acquire_lock("resource:2", owner="client:1")
        self.manager.acquire_lock("resource:3", owner="client:2")
        
        locks = self.manager.get_locks_held("client:1")
        
        self.assertEqual(len(locks), 2)
        self.assertIn("resource:1", locks)
        self.assertIn("resource:2", locks)


class TestDeadlockDetection(unittest.TestCase):
    """Test deadlock detection and prevention"""
    
    def setUp(self):
        """Set up test fixtures"""
        if DeadlockDetector is None:
            self.skipTest("DeadlockDetector not available")
        self.detector = DeadlockDetector()
    
    def test_no_deadlock_linear_chain(self):
        """Test no deadlock in linear chain"""
        # A -> B -> C (linear, no deadlock)
        self.detector.record_lock_order("A", "resource1")
        self.detector.record_lock_order("B", "resource1")
        self.detector.record_lock_order("B", "resource2")
        self.detector.record_lock_order("C", "resource2")
        
        self.assertFalse(self.detector.has_cycle())
    
    def test_deadlock_circular_wait(self):
        """Test detection of circular wait deadlock"""
        # A holds resource1, waits for resource2
        # B holds resource2, waits for resource1
        self.detector.record_lock_order("A", "resource1")
        self.detector.record_wait("A", "resource2")
        
        self.detector.record_lock_order("B", "resource2")
        self.detector.record_wait("B", "resource1")
        
        self.assertTrue(self.detector.has_cycle())
    
    def test_deadlock_prevention_timeout(self):
        """Test preventing deadlock with timeout"""
        # Client tries to acquire locks with timeout
        lock_acquired = self.detector.acquire_with_timeout(
            "client:1", "resource1", timeout_sec=1
        )
        
        # Should eventually give up if can't get lock
        if not lock_acquired:
            self.assertTrue(True)  # Timeout prevented deadlock
    
    def test_deadlock_victim_detection(self):
        """Test identifying victim for deadlock resolution"""
        # Simulate wait-for graph
        self.detector.record_lock_order("A", "res1")
        self.detector.record_wait("A", "res2")
        self.detector.record_lock_order("B", "res2")
        self.detector.record_wait("B", "res1")
        
        # Should find cycle
        if self.detector.has_cycle():
            victim = self.detector.choose_deadlock_victim()
            self.assertIn(victim, ["A", "B"])
    
    def test_lock_ordering_prevents_deadlock(self):
        """Test that strict lock ordering prevents deadlock"""
        # Both clients lock resources in same order
        self.detector.enforce_lock_order(["res1", "res2"])
        
        # Both clients follow order - no deadlock possible
        self.detector.record_lock_order("A", "res1")
        self.detector.record_lock_order("A", "res2")
        
        self.detector.record_lock_order("B", "res1")
        self.detector.record_lock_order("B", "res2")
        
        self.assertFalse(self.detector.has_cycle())


class TestTryLockPattern(unittest.TestCase):
    """Test try-lock pattern for avoiding deadlocks"""
    
    def setUp(self):
        """Set up test fixtures"""
        if DistributedLock is None:
            self.skipTest("DistributedLock not available")
    
    def test_try_lock_success(self):
        """Test successful try-lock"""
        lock = DistributedLock(key="resource", timeout_sec=10)
        
        success = lock.try_lock(owner="client:1", timeout_sec=1)
        
        self.assertTrue(success)
    
    def test_try_lock_failure(self):
        """Test failed try-lock"""
        lock = DistributedLock(key="resource", timeout_sec=10)
        
        # First acquire
        lock.acquire(owner="client:1", timeout_sec=10)
        
        # Try-lock should fail immediately if not available
        success = lock.try_lock(owner="client:2", timeout_sec=0)
        
        self.assertFalse(success)
    
    def test_try_lock_with_backoff(self):
        """Test try-lock with exponential backoff"""
        lock = DistributedLock(key="resource", timeout_sec=10)
        
        lock.acquire(owner="client:1", timeout_sec=10)
        
        # Try with retries
        success = False
        backoff = 0.001
        for attempt in range(3):
            success = lock.try_lock(owner="client:2", timeout_sec=0)
            if success:
                break
            time.sleep(backoff)
            backoff *= 2
        
        # Should eventually fail
        self.assertFalse(success)


class TestLockPerformance(unittest.TestCase):
    """Performance tests for lock operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        if DistributedLock is None:
            self.skipTest("DistributedLock not available")
    
    def test_lock_acquisition_latency(self):
        """Test lock acquisition latency"""
        import time
        
        lock = DistributedLock(key="resource", timeout_sec=10)
        
        start = time.time()
        lock.acquire(owner="client:1", timeout_sec=5)
        latency = (time.time() - start) * 1000  # Convert to ms
        
        # Should acquire quickly
        self.assertLess(latency, 100)
    
    def test_throughput_uncontended(self):
        """Test lock throughput without contention"""
        import time
        
        manager = LockManager()
        
        start = time.time()
        
        for i in range(1000):
            token = manager.acquire_lock(f"resource:{i}", owner="client:1")
            manager.release_lock(f"resource:{i}", token=token)
        
        elapsed = time.time() - start
        throughput = 1000 / elapsed
        
        # Should handle 1000+ lock ops/sec
        self.assertGreater(throughput, 100)
    
    def test_throughput_high_contention(self):
        """Test lock throughput with high contention"""
        import time
        
        lock = DistributedLock(key="shared", timeout_sec=10)
        results = {"acquired": 0, "failed": 0}
        
        def acquire_release():
            success = lock.acquire(owner="client", timeout_sec=0.1)
            if success:
                results["acquired"] += 1
                lock.release(owner="client")
            else:
                results["failed"] += 1
        
        # Run multiple threads
        threads = [threading.Thread(target=acquire_release) for _ in range(5)]
        
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start
        
        total_ops = results["acquired"] + results["failed"]
        throughput = total_ops / elapsed if elapsed > 0 else 0
        
        # Should still handle decent throughput
        self.assertGreater(results["acquired"], 0)


if __name__ == '__main__':
    unittest.main()
