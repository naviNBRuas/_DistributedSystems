"""
Test suite for Merkle Trees

Tests cover:
- Tree construction
- Proof generation and verification
- Diff detection
- Efficiency
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from merkle_tree import MerkleTree


class TestMerkleTree(unittest.TestCase):
    """Test Merkle tree operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data = ["a", "b", "c", "d"]
        self.tree = MerkleTree(self.data)
    
    def test_tree_verification(self):
        """Tree should verify correctly"""
        self.assertTrue(self.tree.verify())
    
    def test_proof_generation(self):
        """Should generate valid proofs"""
        proof = self.tree.generate_proof("b")
        
        # Proof should be list of (side, hash) tuples
        self.assertIsInstance(proof, list)
        self.assertTrue(all(len(item) == 2 for item in proof))
    
    def test_proof_verification(self):
        """Should verify valid proofs"""
        proof = self.tree.generate_proof("c")
        
        is_valid = MerkleTree.verify_proof(
            self.tree.root_hash(),
            "c",
            proof
        )
        
        self.assertTrue(is_valid)
    
    def test_invalid_element_detection(self):
        """Should reject non-existent elements"""
        with self.assertRaises(ValueError):
            self.tree.generate_proof("z")
    
    def test_diff_detection(self):
        """Should detect differences between trees"""
        tree1 = MerkleTree(["a", "b", "c", "d"])
        tree2 = MerkleTree(["a", "b", "X", "d"])  # Different at index 2
        
        diffs = tree1.diff(tree2)
        
        # Should find the difference
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0][0], 2)  # Index
    
    def test_efficient_diff_detection(self):
        """Diff should be O(log N) hashes"""
        large_data = [f"item_{i}" for i in range(1000)]
        tree1 = MerkleTree(large_data)
        
        # Change one item
        large_data_modified = large_data.copy()
        large_data_modified[500] = "MODIFIED"
        tree2 = MerkleTree(large_data_modified)
        
        # Diff should identify the change
        diffs = tree1.diff(tree2)
        self.assertEqual(len(diffs), 1)


class TestProofSize(unittest.TestCase):
    """Test proof efficiency"""
    
    def test_logarithmic_proof_size(self):
        """Proof size should be O(log N)"""
        # Build trees of different sizes
        for size in [16, 256, 1024]:
            data = [f"item_{i}" for i in range(size)]
            tree = MerkleTree(data)
            
            proof = tree.generate_proof("item_0")
            
            # Proof size should be log(size)
            proof_size = len(proof)
            expected_max = 10 + int(__import__('math').log2(size))
            
            self.assertLess(proof_size, expected_max)


if __name__ == '__main__':
    unittest.main(verbosity=2)
