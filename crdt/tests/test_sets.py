import unittest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from g_set import GSet
from two_phase_set import TwoPhaseSet
from or_set import ORSet


class TestGSet(unittest.TestCase):
    def test_basic_ops(self):
        s = GSet()
        s.add("a")
        s.add("b")
        self.assertEqual(s.value(), {"a", "b"})
        
    def test_merge(self):
        s1 = GSet()
        s1.add("a")
        
        s2 = GSet()
        s2.add("b")
        
        s1.merge(s2)
        self.assertEqual(s1.value(), {"a", "b"})
        
        s2.merge(s1)
        self.assertEqual(s2.value(), {"a", "b"})
        
    def test_json(self):
        s = GSet()
        s.add("x")
        json_str = s.to_json()
        s2 = GSet.from_json(json_str)
        self.assertEqual(s.value(), s2.value())


class TestTwoPhaseSet(unittest.TestCase):
    def test_add_remove(self):
        s = TwoPhaseSet()
        s.add("a")
        self.assertIn("a", s.value())
        
        s.remove("a")
        self.assertNotIn("a", s.value())
        
        # Cannot re-add
        s.add("a")
        self.assertNotIn("a", s.value())
        
    def test_merge(self):
        s1 = TwoPhaseSet()
        s1.add("a")
        s1.remove("a") # Removed in s1
        
        s2 = TwoPhaseSet()
        s2.add("a") # Added in s2
        
        # Merge: removal should win if it's in the removed set of anyone
        # Because 2P-set says "if in removed, it's removed".
        # If s1 has 'a' in removed, merging into s2 puts 'a' in s2.removed.
        
        s2.merge(s1)
        self.assertNotIn("a", s2.value())
        
        # Check that unrelated items are preserved
        s1.add("b")
        s2.merge(s1)
        self.assertIn("b", s2.value())


class TestORSet(unittest.TestCase):
    def test_add_wins(self):
        """Test concurrent add/remove behavior (Add-Wins)"""
        s1 = ORSet("n1")
        s2 = ORSet("n2")
        
        s1.add("x")
        # Sync s2 with s1 so s2 knows about "x"
        s2.merge(s1)
        self.assertIn("x", s2.value())
        
        # Concurrent operations:
        # s1 removes "x"
        s1.remove("x")
        self.assertNotIn("x", s1.value())
        
        # s2 adds "x" (new instance)
        s2.add("x")
        
        # Merge
        s1.merge(s2)
        s2.merge(s1)
        
        # Should contain "x" because s2's add is new and wasn't observed by s1's remove
        self.assertIn("x", s1.value())
        self.assertIn("x", s2.value())
        
    def test_remove_effectiveness(self):
        s = ORSet("n1")
        s.add("a")
        s.add("a") # Add again (should be same value but internally maybe multiple tags if called twice? implementation dependent)
        # In my impl, add always generates new tag.
        
        self.assertIn("a", s.value())
        s.remove("a")
        self.assertNotIn("a", s.value())

    def test_merge_associativity(self):
        a = ORSet("a")
        b = ORSet("b")
        c = ORSet("c")
        
        a.add("1")
        b.add("2")
        c.add("3")
        
        # (A+B)+C
        ab = ORSet("ab")
        ab.merge(a)
        ab.merge(b)
        
        abc1 = ORSet("abc1")
        abc1.merge(ab)
        abc1.merge(c)
        
        # A+(B+C)
        bc = ORSet("bc")
        bc.merge(b)
        bc.merge(c)
        
        abc2 = ORSet("abc2")
        abc2.merge(a)
        abc2.merge(bc)
        
        self.assertEqual(abc1.value(), abc2.value())

    def test_json(self):
        s = ORSet("n1")
        s.add("test")
        s.remove("test")
        s.add("test2")
        
        json_str = s.to_json()
        restored = ORSet.from_json(json_str)
        
        self.assertEqual(s.value(), restored.value())

if __name__ == '__main__':
    unittest.main()
