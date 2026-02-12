"""
Test suite for CRDT implementations

Tests cover:
- Merge operations
- Convergence guarantees
- Commutativity and associativity
- Monotonicity
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from g_counter import GCounter
from pn_counter import PNCounter


class TestCRDTProperties(unittest.TestCase):
    """Test CRDT mathematical properties"""
    
    def test_commutativity(self):
        """Merge order shouldn't matter"""
        a = GCounter("a")
        b = GCounter("b")
        c = GCounter("c")
        
        a.increment(1)
        b.increment(2)
        c.increment(3)
        
        # Merge A then B then C
        temp1 = GCounter("temp1")
        temp1.merge(a)
        temp1.merge(b)
        temp1.merge(c)
        result1 = temp1.value()
        
        # Merge C then B then A
        temp2 = GCounter("temp2")
        temp2.merge(c)
        temp2.merge(b)
        temp2.merge(a)
        result2 = temp2.value()
        
        self.assertEqual(result1, result2)
    
    def test_associativity(self):
        """Grouping shouldn't matter"""
        a = GCounter("a")
        b = GCounter("b")
        c = GCounter("c")
        
        a.increment(1)
        b.increment(2)
        c.increment(3)
        
        # (A merge B) merge C
        temp1 = GCounter("temp1")
        temp1.merge(a)
        temp1.merge(b)
        temp1.merge(c)
        result1 = temp1.value()
        
        # A merge (B merge C)
        bc = GCounter("bc")
        bc.merge(b)
        bc.merge(c)
        temp2 = GCounter("temp2")
        temp2.merge(a)
        temp2.merge(bc)
        result2 = temp2.value()
        
        self.assertEqual(result1, result2)
    
    def test_idempotence(self):
        """Merging same state multiple times = once"""
        a = GCounter("a")
        b = GCounter("b")
        
        a.increment(5)
        b.increment(3)
        
        # Merge B into A once
        a.merge(b)
        result1 = a.value()
        
        # Merge B again
        a.merge(b)
        result2 = a.value()
        
        self.assertEqual(result1, result2)
    
    def test_monotonicity(self):
        """Values should never decrease"""
        counter = GCounter("node")
        
        counter.increment(5)
        val1 = counter.value()
        
        counter.increment(3)
        val2 = counter.value()
        
        self.assertGreaterEqual(val2, val1)


class TestGCounter(unittest.TestCase):
    """Test G-Counter specific properties"""
    
    def test_causality_tracking(self):
        """Vector clock should track causality"""
        c1 = GCounter("n1")
        c2 = GCounter("n2")
        
        c1.increment(1)
        c1.increment(2)
        
        c2.increment(1)
        
        # Independent operations are concurrent
        self.assertEqual(c1.compare(c2), "concurrent")
        
        # Now c1 observes c2
        c1.merge(c2)
        # c1 has {n1: 3, n2: 1}
        # c2 has {n2: 1} (implicit n1: 0)
        
        # Now c1 > c2
        self.assertEqual(c1.compare(c2), "greater")
        self.assertEqual(c2.compare(c1), "less")


class TestPNCounter(unittest.TestCase):
    """Test PN-Counter specific properties"""
    
    def test_concurrent_inc_dec(self):
        """Should handle concurrent increments and decrements"""
        c1 = PNCounter("n1")
        c2 = PNCounter("n2")
        
        c1.increment(10)
        c2.decrement(3)
        
        # Merge
        c1.merge(c2)
        c2.merge(c1)
        
        # Both should converge
        self.assertEqual(c1.value(), c2.value())
        self.assertEqual(c1.value(), 7)


if __name__ == '__main__':
    unittest.main(verbosity=2)
