
import unittest
from src.vector_clock_advanced import DottedVersionVector, IntervalTreeClock

class TestDottedVersionVector(unittest.TestCase):
    def test_basic_vector_clock_behavior(self):
        v1 = DottedVersionVector("A")
        v2 = DottedVersionVector("B")
        
        v1.event() # A:1
        v2.event() # B:1
        
        # They should be concurrent
        self.assertTrue(v1.concurrent(v2))
        self.assertFalse(v1.happens_before(v2))
        self.assertFalse(v2.happens_before(v1))
        
        # Merge
        v1.merge(v2) # A:1, B:1
        
        # Now v2 < v1
        self.assertTrue(v2.happens_before(v1))
        self.assertFalse(v1.happens_before(v2))
        
    def test_missing_keys_handling(self):
        """Test that missing keys in 'self' are correctly handled during comparison"""
        v1 = DottedVersionVector("A")
        v1.event() # A:1
        
        v2 = DottedVersionVector("B")
        v2.event() # B:1
        v2.merge(v1) # A:1, B:1
        
        # v1 (A:1) is strictly less than v2 (A:1, B:1).
        # v1 is missing B, which implies B:0.
        # v2 has B:1.
        
        self.assertTrue(v1.happens_before(v2), "v1 should happen before v2")

    def test_dots_causality(self):
        """Test if dots are considered in causality"""
        v1 = DottedVersionVector("A")
        v1.clock = {"A": 0}
        v1.dots = {("A", 2)} # Gap! 1 is missing
        
        v2 = DottedVersionVector("B")
        v2.clock = {"A": 2} # contiguous 1, 2
        
        # v1 knows {A:2}. v2 knows {A:1, A:2}.
        # v1 is missing A:1. v2 has A:1.
        # v1 is strictly a subset of v2's knowledge.
        self.assertTrue(v1.happens_before(v2))

    def test_increment_gap_behavior(self):
        """
        Verify what happens when we increment with a gap.
        Correct behavior: clock stays at 5, dot added at 10.
        """
        dvv = DottedVersionVector("A")
        dvv.clock = {"A": 5}
        
        # Jump to 10
        dvv.increment(10)
        
        # New behavior: clock stays 5 because 6..9 are missing.
        self.assertEqual(dvv.clock["A"], 5)
        self.assertIn(("A", 10), dvv.dots)
        
    def test_semantic_equality(self):
        """
        Test if compact and non-compact versions are equal.
        """
        v1 = DottedVersionVector("A")
        v1.clock = {"A": 2}
        
        v2 = DottedVersionVector("A")
        v2.clock = {"A": 1}
        v2.dots = {("A", 2)}
        
        # Semantically they represent the same history {A:1, A:2}
        self.assertEqual(v1, v2)
        self.assertTrue(v1.is_subset(v2))
        self.assertTrue(v2.is_subset(v1))

    def test_subset_logic_complex(self):
        # A:1, B:1
        v1 = DottedVersionVector("A")
        v1.clock = {"A": 1, "B": 1}
        
        # A:1, B:1, dot A:2
        v2 = DottedVersionVector("B")
        v2.clock = {"A": 1, "B": 1}
        v2.dots = {("A", 2)}
        
        self.assertTrue(v1 <= v2)
        self.assertFalse(v2 <= v1)
        
        # Gap case
        # v3: A:1, B:1, dot A:3 (missing A:2)
        v3 = DottedVersionVector("C")
        v3.clock = {"A": 1, "B": 1}
        v3.dots = {("A", 3)}
        
        # v2 (has A:2) vs v3 (has A:3, missing A:2)
        # v2 <= v3? No, v3 missing A:2.
        self.assertFalse(v2 <= v3)
        
        # v3 <= v2? No, v2 missing A:3.
        self.assertFalse(v3 <= v2)
        
        self.assertTrue(v2.concurrent(v3))

class TestIntervalTreeClock(unittest.TestCase):
    def test_basic_usage(self):
        itc = IntervalTreeClock("root")
        itc.increment()
        child = itc.fork("child")
        self.assertEqual(child.counter, 1)

if __name__ == '__main__':
    unittest.main()
