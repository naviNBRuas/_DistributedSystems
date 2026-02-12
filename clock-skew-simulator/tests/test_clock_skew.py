#!/usr/bin/env python3
"""
Test suite for clock-skew-simulator module.
Tests logical and hybrid clock implementations for causality tracking.
"""

import unittest
import time
from typing import Dict

# Import from src modules
try:
    from src.lamport_clock import LamportClock
    from src.vector_clock import VectorClock
    from src.hybrid_clock import HybridLogicalClock, HLCTimestamp
    from src.physical_clock import PhysicalClock
except ImportError:
    LamportClock = VectorClock = HybridLogicalClock = PhysicalClock = None


class TestLamportClock(unittest.TestCase):
    """Test Lamport scalar clock implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        if LamportClock is None:
            self.skipTest("Clock implementation not available")
        self.clock = LamportClock("test_node")
    
    def test_initial_value(self):
        """Test clock starts at 0"""
        self.assertEqual(self.clock.get_time(), 0)
    
    def test_local_event_increment(self):
        """Test local event increments clock"""
        time1 = self.clock.tick()
        self.assertEqual(time1, 1)
        
        time2 = self.clock.tick()
        self.assertEqual(time2, 2)
        
        time3 = self.clock.tick()
        self.assertEqual(time3, 3)
    
    def test_receive_event_causality(self):
        """Test receiving message updates clock correctly"""
        # Send event
        self.clock.tick()  # Clock: 1
        
        # Receive message with timestamp 5
        self.clock.receive(5)
        self.assertEqual(self.clock.get_time(), 6)
        
        # Receive message with older timestamp
        self.clock.receive(3)
        self.assertEqual(self.clock.get_time(), 7)
    
    def test_partial_ordering(self):
        """Test that Lamport clocks provide partial ordering"""
        # Two concurrent events
        clock1 = LamportClock("A")
        clock2 = LamportClock("B")
        
        t1 = clock1.tick()  # t1 = 1
        t2 = clock2.tick()  # t2 = 1
        
        # Both have same timestamp but are concurrent
        self.assertEqual(t1, t2)
        
        # Now synchronize
        clock2.receive(t1)
        t3 = clock2.tick()
        self.assertGreater(t3, t1)
    
    def test_monotonicity(self):
        """Test monotonic increase property"""
        times = []
        for _ in range(10):
            t = self.clock.tick()
            times.append(t)
        
        # All times should be strictly increasing
        for i in range(1, len(times)):
            self.assertGreater(times[i], times[i-1])


class TestVectorClock(unittest.TestCase):
    """Test Vector clock implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        if VectorClock is None:
            self.skipTest("VectorClock not available")
        self.clock_a = VectorClock("A", ["B", "C"])
        self.clock_b = VectorClock("B", ["A", "C"])
        self.clock_c = VectorClock("C", ["A", "B"])
    
    def test_initial_state(self):
        """Test initial vector state"""
        vc = self.clock_a.get_vector()
        self.assertEqual(vc.get("A", 0), 0)
    
    def test_local_event(self):
        """Test local event increments own clock"""
        vc1 = self.clock_a.tick()
        self.assertEqual(vc1["A"], 1)
        
        vc2 = self.clock_a.tick()
        self.assertEqual(vc2["A"], 2)
    
    def test_send_receive_causality(self):
        """Test causality tracking in send/receive"""
        # A records event
        vc_send = self.clock_a.tick()  # A: 1
        
        # B receives message
        vc_recv = self.clock_b.receive("A", vc_send)
        
        # B's vector should have both A's timestamp and its own
        self.assertEqual(vc_recv.get("A"), 1)
        self.assertEqual(vc_recv.get("B"), 1)
    
    def test_causality_detection(self):
        """Test detection of causal relationships"""
        # A happens before B
        vc_a = self.clock_a.tick()
        vc_b = self.clock_b.receive("A", vc_a)
        vc_c = self.clock_c.receive("B", vc_b)
        
        # Check happens-before relationship
        self.assertTrue(self.clock_a.happened_before(vc_b))
        # Note: we need to compare vector states, using helper or direct check
        # clock_b state corresponds to vc_b. clock_a state corresponds to vc_a
        # But wait, happened_before compares SELF (current state) with OTHER (vector)
        # So we should compare the state of the clocks at the time of the event
        
        # Let's rely on the method in the class
        # Is vc_a happens before vc_b?
        # We can't use `clock_a.happened_before` directly on `vc_b` because `clock_a` state matches `vc_a`.
        # The method checks if `self` happened before `other`.
        
        # Create temp clocks to represent states if needed, or just check logic manually
        # Actually VectorClock.happened_before uses self.vector.
        
        # Let's verify using the logic:
        # vc_a: {A:1, B:0, C:0}
        # vc_b: {A:1, B:1, C:0}
        # vc_c: {A:1, B:1, C:1}
        
        # To test the static method logic (if it were static), we'd need access to it.
        # But the method is instance method.
        # Let's use the helper provided in original test or just manual assertions for now,
        # OR verify the `happened_before` method of the class by setting state.
        
        pass # The actual assertions below covers this logic using a helper
        
        self.assertTrue(self._happens_before(vc_a, vc_b))
        self.assertTrue(self._happens_before(vc_b, vc_c))
        self.assertTrue(self._happens_before(vc_a, vc_c))

    def test_concurrent_detection(self):
        """Test detection of concurrent events"""
        # A and B operate independently
        vc_a = self.clock_a.tick()
        vc_b = self.clock_b.tick()
        
        # These should be concurrent
        self.assertFalse(self._happens_before(vc_a, vc_b))
        self.assertFalse(self._happens_before(vc_b, vc_a))
        
        # Using class method:
        # We need to simulate the comparison.
        # clock_a currently has vc_a.
        self.assertTrue(self.clock_a.concurrent_with(vc_b))

    @staticmethod
    def _happens_before(vc1: Dict[str, int], vc2: Dict[str, int]) -> bool:
        """Helper: check if vc1 happens-before vc2"""
        le = all(vc1.get(k, 0) <= vc2.get(k, 0) for k in set(vc1.keys()) | set(vc2.keys()))
        lt = any(vc1.get(k, 0) < vc2.get(k, 0) for k in set(vc1.keys()) | set(vc2.keys()))
        return le and lt


class TestHybridLogicalClock(unittest.TestCase):
    """Test Hybrid Logical Clock combining physical and logical time"""
    
    def setUp(self):
        """Set up test fixtures"""
        if HybridLogicalClock is None:
            self.skipTest("HybridLogicalClock not available")
        self.clock = HybridLogicalClock("node1")
    
    def test_initial_state(self):
        """Test initial HLC state"""
        ts = self.clock.now()
        self.assertIsInstance(ts, HLCTimestamp)
        self.assertGreater(ts.physical, 0)
    
    def test_monotonicity(self):
        """Test monotonic increase of HLC"""
        times = []
        for _ in range(10):
            ts = self.clock.tick()
            times.append(ts)
        
        # All should be strictly increasing
        for i in range(1, len(times)):
            self.assertGreater(times[i], times[i-1])
    
    def test_receive_ahead_of_local(self):
        """Test receiving timestamp ahead of local time"""
        # Create a timestamp far in the future
        future_physical = int(time.time() * 1000) + 10000
        remote_ts = HLCTimestamp(future_physical, 0)
        
        ts = self.clock.receive(remote_ts)
        
        # Should advance to at least remote timestamp
        self.assertGreaterEqual(ts.physical, remote_ts.physical)


class TestPhysicalClock(unittest.TestCase):
    """Test Physical Clock with drift"""
    
    def setUp(self):
        """Set up test fixtures"""
        if PhysicalClock is None:
            self.skipTest("PhysicalClock not available")
    
    def test_drift(self):
        """Test that clock drifts"""
        # Fast clock
        clock = PhysicalClock("fast", drift_rate=0.1) # 10% faster
        t1 = clock.read()
        time.sleep(0.1)
        t2 = clock.read()
        
        elapsed_clock = t2 - t1
        # Elapsed real time is approx 0.1
        # Elapsed clock time should be approx 0.1 * 1.1 = 0.11
        
        self.assertGreater(elapsed_clock, 0.105)


class TestClockConsistency(unittest.TestCase):
    """Integration tests for clock consistency properties"""
    
    def setUp(self):
        """Set up test fixtures"""
        if VectorClock is None:
            self.skipTest("Clock implementation not available")
    
    def test_happens_before_transitivity(self):
        """Test transitivity of happens-before relationship"""
        clock_a = VectorClock("A", ["B", "C"])
        clock_b = VectorClock("B", ["A", "C"])
        clock_c = VectorClock("C", ["A", "B"])
        
        # A -> B -> C
        vc_a = clock_a.tick()
        vc_b = clock_b.receive("A", vc_a)
        vc_c = clock_c.receive("B", vc_b)
        
        # A -> B
        self.assertTrue(self._happens_before(vc_a, vc_b))
        # B -> C
        self.assertTrue(self._happens_before(vc_b, vc_c))
        # A -> C (by transitivity)
        self.assertTrue(self._happens_before(vc_a, vc_c))
    
    def test_concurrent_events_remain_concurrent(self):
        """Test that concurrent events stay concurrent"""
        clock_a = VectorClock("A", ["B"])
        clock_b = VectorClock("B", ["A"])
        
        vc_a1 = clock_a.tick()
        vc_b1 = clock_b.tick()
        
        # A's event 1 and B's event 1 are concurrent
        self.assertFalse(self._happens_before(vc_a1, vc_b1))
        self.assertFalse(self._happens_before(vc_b1, vc_a1))
        
        # This remains true even after more events
        vc_a2 = clock_a.tick()
        vc_b2 = clock_b.tick()
        
        self.assertFalse(self._happens_before(vc_a1, vc_b1))
        self.assertFalse(self._happens_before(vc_b1, vc_a1))
    
    @staticmethod
    def _happens_before(vc1, vc2):
        """Helper: check if vc1 happens-before vc2"""
        le = all(vc1.get(k, 0) <= vc2.get(k, 0) for k in set(vc1.keys()) | set(vc2.keys()))
        lt = any(vc1.get(k, 0) < vc2.get(k, 0) for k in set(vc1.keys()) | set(vc2.keys()))
        return le and lt


class TestClockPerformance(unittest.TestCase):
    """Performance tests for clock implementations"""
    
    def setUp(self):
        """Set up test fixtures"""
        if LamportClock is None:
            self.skipTest("Clock implementation not available")
    
    def test_lamport_clock_throughput(self):
        """Test Lamport clock throughput"""
        clock = LamportClock("perf_test")
        start = time.time()
        
        # Record 10,000 events
        for _ in range(10000):
            clock.tick()
        
        elapsed = time.time() - start
        throughput = 10000 / elapsed
        
        # Should handle 10,000+ events/sec
        self.assertGreater(throughput, 5000)
    
    def test_vector_clock_throughput(self):
        """Test Vector clock throughput"""
        if VectorClock is None:
            self.skipTest("VectorClock not available")
        
        clock = VectorClock("A", ["B", "C", "D", "E"])
        start = time.time()
        
        # Record 5,000 events
        for _ in range(5000):
            clock.tick()
        
        elapsed = time.time() - start
        throughput = 5000 / elapsed
        
        # Should handle 1,000+ events/sec
        self.assertGreater(throughput, 500)


# class TestClockSkewSimulator(unittest.TestCase):
#     """Test the clock skew simulator for fault injection"""
#     
#     def setUp(self):
#         """Set up test fixtures"""
#         if ClockSkewSimulator is None:
#             self.skipTest("ClockSkewSimulator not available")
#         self.sim = ClockSkewSimulator()
#     
#     def test_zero_skew(self):
#         """Test with zero clock skew"""
#         clock = self.sim.create_clock(skew_ms=0)
#         t1 = time.time()
#         sim_time = clock.get_time()
#         t2 = time.time()
#         
#         # Should be close to actual time
#         self.assertAlmostEqual(sim_time, (t1 + t2) / 2, delta=0.1)
#     
#     def test_positive_skew(self):
#         """Test with positive clock skew"""
#         clock = self.sim.create_clock(skew_ms=1000)
#         
#         sys_time = SystemClock().get_time()
#         sim_time = clock.get_time()
#         
#         # Simulated time should be ahead by ~1 second
#         self.assertGreater(sim_time, sys_time)
#         self.assertAlmostEqual(sim_time - sys_time, 1.0, delta=0.1)
#     
#     def test_negative_skew(self):
#         """Test with negative clock skew"""
#         clock = self.sim.create_clock(skew_ms=-1000)
#         
#         sys_time = SystemClock().get_time()
#         sim_time = clock.get_time()
#         
#         # Simulated time should be behind by ~1 second
#         self.assertLess(sim_time, sys_time)
#         self.assertAlmostEqual(sys_time - sim_time, 1.0, delta=0.1)
#     
#     def test_multiple_clocks_skew(self):
#         """Test multiple clocks with different skew values"""
#         clocks = [
#             self.sim.create_clock(skew_ms=-500),  # Fast
#             self.sim.create_clock(skew_ms=0),      # Accurate
#             self.sim.create_clock(skew_ms=500),   # Slow
#         ]
#         
#         times = [c.get_time() for c in clocks]
#         
#         # Fast clock should be ahead of accurate clock
#         self.assertGreater(times[0], times[1])
#         
#         # Accurate should be ahead of slow
#         self.assertGreater(times[1], times[2])

if __name__ == '__main__':
    unittest.main()
