import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from causal_context import CausalContext


class TestCausalContext(unittest.TestCase):
    def test_increment(self):
        cc = CausalContext("n1")
        cc.increment()
        self.assertEqual(cc.value()["n1"], 1)
        
    def test_compare(self):
        c1 = CausalContext("n1")
        c2 = CausalContext("n2")
        
        c1.increment() # {n1: 1}
        # {n2: 0} effectively
        
        self.assertEqual(c1.compare(c2), "greater") # n1:1 > n1:0 (implicit)
        
        c2.increment() # {n2: 1}
        # Now c1 has {n1:1, n2:0}, c2 has {n1:0, n2:1}
        self.assertEqual(c1.compare(c2), "concurrent")
        
        c1.merge(c2) # c1: {n1:1, n2:1}
        self.assertEqual(c1.compare(c2), "greater")
        
    def test_merge(self):
        c1 = CausalContext("n1")
        c1.increment()
        
        c2 = CausalContext("n2")
        c2.increment()
        c2.increment()
        
        c1.merge(c2)
        val = c1.value()
        self.assertEqual(val["n1"], 1)
        self.assertEqual(val["n2"], 2)

if __name__ == '__main__':
    unittest.main()
