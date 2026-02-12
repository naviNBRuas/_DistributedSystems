import unittest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from lww_register import LWWRegister
from lww_map import LWWMap


class TestLWWRegister(unittest.TestCase):
    def test_lww_behavior(self):
        r1 = LWWRegister("n1")
        r1.write("v1", timestamp=100)
        
        r2 = LWWRegister("n2")
        r2.write("v2", timestamp=200)
        
        r1.merge(r2)
        self.assertEqual(r1.value(), "v2") # Higher timestamp wins
        
        r2.merge(r1)
        self.assertEqual(r2.value(), "v2")
        
    def test_tie_breaking(self):
        # Same timestamp, different values. Tie break by node_id
        # n2 > n1
        r1 = LWWRegister("n1")
        r1.write("v1", timestamp=100)
        
        r2 = LWWRegister("n2")
        r2.write("v2", timestamp=100)
        
        r1.merge(r2)
        self.assertEqual(r1.value(), "v2") # n2 > n1
        
    def test_local_update(self):
        r = LWWRegister("n1")
        r.write("old", timestamp=100)
        r.write("new", timestamp=101)
        self.assertEqual(r.value(), "new")
        
        # Write with old timestamp should be ignored (unless logic allows overwrite if strictly local? LWW usually strictly follows TS)
        r.write("older", timestamp=50)
        self.assertEqual(r.value(), "new")


class TestLWWMap(unittest.TestCase):
    def test_put_get(self):
        m = LWWMap("n1")
        m.put("k1", "v1")
        self.assertEqual(m.get("k1"), "v1")
        
    def test_remove(self):
        m = LWWMap("n1")
        m.put("k1", "v1", timestamp=100)
        m.remove("k1", timestamp=101)
        self.assertIsNone(m.get("k1"))
        
        # Older put shouldn't resurrect it
        m.put("k1", "v2", timestamp=99)
        self.assertIsNone(m.get("k1"))
        
        # Newer put should resurrect it
        m.put("k1", "v3", timestamp=102)
        self.assertEqual(m.get("k1"), "v3")
        
    def test_merge(self):
        m1 = LWWMap("n1")
        m1.put("shared", "v1", timestamp=100)
        m1.put("only_m1", "x")
        
        m2 = LWWMap("n2")
        m2.put("shared", "v2", timestamp=200)
        m2.put("only_m2", "y")
        
        m1.merge(m2)
        
        self.assertEqual(m1.get("shared"), "v2") # LWW
        self.assertEqual(m1.get("only_m1"), "x")
        self.assertEqual(m1.get("only_m2"), "y")
        
    def test_json(self):
        m = LWWMap("n1")
        m.put("a", 1)
        m.put("b", 2)
        
        json_str = m.to_json()
        restored = LWWMap.from_json(json_str)
        
        self.assertEqual(restored.get("a"), 1)
        self.assertEqual(restored.get("b"), 2)

if __name__ == '__main__':
    unittest.main()
