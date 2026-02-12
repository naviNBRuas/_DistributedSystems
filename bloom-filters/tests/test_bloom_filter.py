import unittest
import math
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from bloom_filter import BloomFilter, CountingBloomFilter, ScalableBloomFilter

class TestBloomFilter(unittest.TestCase):
    def test_basic_functionality(self):
        bf = BloomFilter(expected_elements=100, false_positive_rate=0.01)
        bf.add("test")
        self.assertTrue("test" in bf)
        self.assertFalse("nonexistent" in bf)

    def test_false_positive_rate_approx(self):
        # This is probabilistic, so we allow some margin
        n = 1000
        p = 0.05
        bf = BloomFilter(expected_elements=n, false_positive_rate=p)
        for i in range(n):
            bf.add(f"item_{i}")
        
        false_positives = 0
        trials = 1000
        for i in range(trials):
            if f"nonexistent_{i}" in bf:
                false_positives += 1
        
        observed_p = false_positives / trials
        # Check if observed rate is within reasonable bounds (e.g. 2x target)
        self.assertLess(observed_p, p * 2.5)

    def test_counting_bloom_filter(self):
        cbf = CountingBloomFilter(expected_elements=100, false_positive_rate=0.01)
        cbf.add("test")
        self.assertTrue("test" in cbf)
        cbf.remove("test")
        self.assertFalse("test" in cbf)

    def test_scalable_bloom_filter(self):
        sbf = ScalableBloomFilter(initial_size=50, false_positive_rate=0.01)
        # Add more than initial size
        for i in range(200):
            sbf.add(f"item_{i}")
        
        self.assertTrue("item_0" in sbf)
        self.assertTrue("item_199" in sbf)
        self.assertFalse("nonexistent" in sbf)
        # Should have grown
        self.assertGreater(len(sbf.filters), 1)

if __name__ == '__main__':
    unittest.main()
