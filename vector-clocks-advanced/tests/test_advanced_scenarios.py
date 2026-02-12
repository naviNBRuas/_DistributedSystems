
import unittest
from src.vector_clock_advanced import DottedVersionVector, IntervalTreeClock, CausalHistory

class TestAdvancedDVV(unittest.TestCase):
    def test_compact_dots(self):
        """Test that dots are correctly compacted into the clock"""
        dvv = DottedVersionVector("A")
        # Manually set state to simulate a received state with dots
        dvv.clock = {"A": 2}
        dvv.dots = {("A", 3), ("A", 4), ("A", 6)} 
        # 3 and 4 are contiguous to 2, so should be compacted -> clock=4
        # 6 is a gap, should remain in dots
        
        dvv._compact_dots()
        
        self.assertEqual(dvv.clock["A"], 4)
        self.assertEqual(dvv.dots, {("A", 6)})
        
    def test_merge_with_gap_filling(self):
        """Test merging fills gaps and compacts"""
        # Node A: has 1..4
        v1 = DottedVersionVector("A")
        v1.clock = {"A": 4}
        
        # Node B: has A:1..2 and dot A:4 (missing A:3)
        v2 = DottedVersionVector("B")
        v2.clock = {"A": 2}
        v2.dots = {("A", 4)}
        
        # Merge v2 into v1? No, v1 has more info.
        # Merge v1 into v2.
        v2.merge(v1)
        
        # v2 should now have A:4 (max of 2 and 4, plus dots)
        self.assertEqual(v2.clock["A"], 4)
        # dots should be empty because A:4 covers everything
        self.assertEqual(len(v2.dots), 0)

    def test_concurrent_complex(self):
        v1 = DottedVersionVector("A")
        v2 = DottedVersionVector("B")
        
        v1.event() # A:1
        v2.event() # B:1
        
        v1.event() # A:2
        
        # v1: {A:2}, v2: {B:1}
        self.assertTrue(v1.concurrent(v2))
        
        # Create a cross dependency without full merge
        # Simulate v3 that saw A:1 and B:1
        v3 = DottedVersionVector("C")
        v3.clock = {"A": 1, "B": 1}
        
        # v3 < v1? 
        # v3 knows A:1, B:1. v1 knows A:2 (so A:1, A:2) and B:0.
        # v1 is missing B:1. So v3 is NOT <= v1.
        self.assertFalse(v3 <= v1)
        
        # v1 < v3?
        # v1 has A:2. v3 has A:1.
        # v1 is NOT <= v3.
        self.assertFalse(v1 <= v3)
        
        self.assertTrue(v1.concurrent(v3))

    def test_serialization(self):
        v1 = DottedVersionVector("A")
        v1.event()
        v1.dots.add(("B", 5))
        
        data = v1.to_dict()
        v2 = DottedVersionVector.from_dict(data)
        
        self.assertEqual(v1, v2)
        self.assertEqual(v2.clock["A"], 1)
        self.assertIn(("B", 5), v2.dots)

class TestITCWrapper(unittest.TestCase):
    def test_fork_join(self):
        root = IntervalTreeClock("root")
        root.increment() # root:1
        
        child = root.fork("child") # child:1
        
        root.increment() # root:2
        child.increment() # child:2
        
        # Disconnected updates
        
        joined = root.join(child)
        # Should be max(2,2) = 2
        self.assertEqual(joined.counter, 2)
        self.assertIn("child", joined.children)
        
        child.increment() # child:3
        joined2 = root.join(child)
        self.assertEqual(joined2.counter, 3) # max(2, 3)
        
    def test_prune(self):
        root = IntervalTreeClock("root")
        root.counter = 5
        
        child = root.fork("c1") # c1: 5
        
        # child is redundant
        root.prune()
        # Should remove c1
        self.assertNotIn("c1", root.children)
        
        # Create non-redundant
        child2 = root.fork("c2")
        child2.increment() # c2: 6
        
        root.prune()
        self.assertIn("c2", root.children)

class TestCausalHistory(unittest.TestCase):
    def test_history(self):
        h1 = CausalHistory("A")
        ts1 = h1.record_event("evt1")
        ts2 = h1.record_event("evt2")
        
        self.assertEqual(ts1, 1)
        self.assertEqual(ts2, 2)
        
        h2 = CausalHistory("B")
        h2.merge_history(h1)
        
        self.assertEqual(h2.dvv.clock["A"], 2)

if __name__ == '__main__':
    unittest.main()
