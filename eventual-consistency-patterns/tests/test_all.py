import unittest
import time
from typing import Dict, Optional

from eventual_consistency.models import VectorClock, VersionedValue, Ordering
from eventual_consistency.conflict_resolution import resolve_lww, resolve_vector_clock
from eventual_consistency.read_repair import ReadRepair, Replica
from eventual_consistency.anti_entropy import MerkleTree, MerkleSync
from eventual_consistency.causal import CausalSession

# --- Mocks ---
class MockReplica(Replica):
    def __init__(self, data: Dict[str, VersionedValue] = None):
        self.store = data if data else {}
        self.put_calls = []

    def get(self, key: str) -> Optional[VersionedValue]:
        return self.store.get(key)

    def put(self, key: str, value: VersionedValue) -> None:
        self.store[key] = value
        self.put_calls.append((key, value))

class TestVectorClock(unittest.TestCase):
    def test_increment(self):
        vc = VectorClock()
        vc.increment("A")
        self.assertEqual(vc.clock["A"], 1)
        vc.increment("A")
        self.assertEqual(vc.clock["A"], 2)

    def test_merge(self):
        vc1 = VectorClock({"A": 1, "B": 2})
        vc2 = VectorClock({"A": 2, "C": 1})
        vc1.merge(vc2)
        self.assertEqual(vc1.clock, {"A": 2, "B": 2, "C": 1})

    def test_compare(self):
        v1 = VectorClock({"A": 1})
        v2 = VectorClock({"A": 2})
        self.assertEqual(v1.compare(v2), Ordering.LT)
        self.assertEqual(v2.compare(v1), Ordering.GT)
        
        v3 = VectorClock({"A": 1, "B": 1})
        self.assertEqual(v1.compare(v3), Ordering.LT)

        v4 = VectorClock({"B": 2})
        self.assertEqual(v1.compare(v4), Ordering.CONCURRENT)

class TestConflictResolution(unittest.TestCase):
    def test_lww(self):
        v1 = VersionedValue("old", timestamp=100)
        v2 = VersionedValue("new", timestamp=200)
        self.assertEqual(resolve_lww(v1, v2).value, "new")
        self.assertEqual(resolve_lww(v2, v1).value, "new")

    def test_vector_resolution(self):
        vc1 = VectorClock({"A": 1})
        vc2 = VectorClock({"A": 2})
        val1 = VersionedValue("v1", vector_clock=vc1)
        val2 = VersionedValue("v2", vector_clock=vc2)
        
        # v2 > v1
        self.assertEqual(resolve_vector_clock(val1, val2).value, "v2")

        # Concurrent
        vc3 = VectorClock({"B": 1})
        val3 = VersionedValue("v3", vector_clock=vc3)
        
        # Should fallback to LWW or merge. Since no merge_func, LWW.
        # Let's ensure timestamps differ to test LWW fallback
        val1.timestamp = 100
        val3.timestamp = 200
        self.assertEqual(resolve_vector_clock(val1, val3).value, "v3")

class TestReadRepair(unittest.TestCase):
    def test_read_repair(self):
        latest_val = VersionedValue("latest", timestamp=200)
        stale_val = VersionedValue("stale", timestamp=100)
        
        r1 = MockReplica({"key1": latest_val})
        r2 = MockReplica({"key1": stale_val})
        r3 = MockReplica({}) # Missing key

        rr = ReadRepair([r1, r2, r3])
        result = rr.read("key1")
        
        # Ensure async repairs complete
        rr.shutdown()

        self.assertEqual(result.value, "latest")
        
        # r2 should be repaired
        self.assertEqual(len(r2.put_calls), 1)
        self.assertEqual(r2.put_calls[0][1].value, "latest")

        # r3 should be repaired (missing)
        self.assertEqual(len(r3.put_calls), 1)
        self.assertEqual(r3.put_calls[0][1].value, "latest")
        
        # r1 should not be repaired
        self.assertEqual(len(r1.put_calls), 0)

class TestAntiEntropy(unittest.TestCase):
    def test_merkle_sync(self):
        val1 = VersionedValue("data1", timestamp=100)
        val2 = VersionedValue("data2", timestamp=100)
        
        data1 = {"k1": val1, "k2": val2}
        data2 = {"k1": val1} # Missing k2
        
        # Small buckets to force collisions or easy structure
        tree1 = MerkleTree(data1, num_buckets=4)
        tree2 = MerkleTree(data2, num_buckets=4)
        
        sync = MerkleSync()
        diffs = sync.compare_trees(tree1, tree2)
        
        self.assertIn("k2", diffs)
        # k1 is same, so should not be in diffs (unless bucket collision with k2)
        # With 4 buckets, collision chance is high.
        # k1 hash might map to same bucket as k2.
        # If they map to same bucket, the bucket hash differs, so BOTH k1 and k2 are returned.
        # Let's check if we can distinguish.
        # The logic is: if bucket differs, return all keys in bucket.
        # So if collision, we get k1 too. That's acceptable for this pattern (false positives are safe).
        
        # Let's try to verify they are in different buckets or same.
        b1 = tree1._hash_key("k1")
        b2 = tree1._hash_key("k2")
        if b1 != b2:
            self.assertNotIn("k1", diffs)
        else:
            self.assertIn("k1", diffs)

class TestCausal(unittest.TestCase):
    def test_causal_check(self):
        session = CausalSession("client1")
        session.clock = VectorClock({"A": 5, "B": 2})
        
        # Consistent read: {A: 5, B: 2}
        v1 = VersionedValue("valid", vector_clock=VectorClock({"A": 5, "B": 2}))
        self.assertTrue(session.check_consistency(v1))
        
        # Future read: {A: 6} -> Valid (advances time)
        v2 = VersionedValue("future", vector_clock=VectorClock({"A": 6, "B": 2}))
        self.assertTrue(session.check_consistency(v2))
        
        # Stale read: {A: 4} -> Invalid (violates Monotonic Reads)
        v3 = VersionedValue("stale", vector_clock=VectorClock({"A": 4, "B": 2}))
        self.assertFalse(session.check_consistency(v3))

if __name__ == '__main__':
    unittest.main()
