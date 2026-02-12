"""
Merkle Tree Implementation

Cryptographic hash tree for efficient data verification
and synchronization in distributed systems.
"""

import hashlib
from typing import List, Tuple, Optional, Any


class MerkleNode:
    """
    Node in a Merkle tree
    
    Each node contains:
    - data: The actual data (for leaves)
    - hash: SHA256 hash of data or children
    - left/right: Child nodes
    - width: Number of leaves in this subtree
    """
    
    def __init__(self, data: Optional[Any] = None, left: Optional['MerkleNode'] = None, right: Optional['MerkleNode'] = None):
        self.data = data
        self.left = left
        self.right = right
        
        # Calculate width (number of leaves)
        if self.left is None and self.right is None:
            self.width = 1
        else:
            w_left = self.left.width if self.left else 0
            w_right = self.right.width if self.right else 0
            self.width = w_left + w_right
            
        self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute hash for this node"""
        if self.is_leaf():
            # Leaf node: hash of data
            return hashlib.sha256(str(self.data).encode()).hexdigest()
        else:
            # Internal node: hash of concatenated children hashes
            # Note: In this implementation, we promote odd nodes, so 'right' might be None 
            # only if we allowed single-child parents, but _build_tree promotes the child directly.
            # However, for safety/completeness:
            left_hash = self.left.hash if self.left else ""
            right_hash = self.right.hash if self.right else ""
            combined = left_hash + right_hash
            return hashlib.sha256(combined.encode()).hexdigest()
    
    def is_leaf(self) -> bool:
        """Check if node is a leaf"""
        return self.left is None and self.right is None
    
    def __repr__(self):
        if self.is_leaf():
            return f"Leaf({self.data}, {self.hash[:8]}...)"
        return f"Node(w={self.width}, {self.hash[:8]}...)"


class MerkleTree:
    """
    Merkle Tree for data verification and synchronization
    
    Features:
    - Build tree from data blocks (handles odd number of leaves by promoting nodes)
    - Generate proofs of inclusion
    - Efficient diff detection
    - Root hash for verification
    """
    
    def __init__(self, data_blocks: List[Any]):
        """
        Initialize Merkle tree
        
        Args:
            data_blocks: List of data to store in leaves
        """
        if not data_blocks:
            raise ValueError("Cannot create empty Merkle tree")
        
        self.leaves = [MerkleNode(data=block) for block in data_blocks]
        self.root = self._build_tree(self.leaves[:])
    
    def _build_tree(self, nodes: List[MerkleNode]) -> MerkleNode:
        """
        Build tree bottom-up
        
        Args:
            nodes: List of nodes at current level
            
        Returns:
            Root node of tree
        """
        if len(nodes) == 1:
            return nodes[0]
        
        # Create parent level
        parents = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            if i + 1 < len(nodes):
                right = nodes[i + 1]
                parent = MerkleNode(left=left, right=right)
                parents.append(parent)
            else:
                # Odd number of nodes: promote the last node to the next level
                parents.append(left)
        
        return self._build_tree(parents)
    
    def root_hash(self) -> str:
        """Get root hash of tree"""
        return self.root.hash
    
    def verify(self) -> bool:
        """Verify tree integrity (recalculate all hashes)"""
        return self._verify_node(self.root)
    
    def _verify_node(self, node: MerkleNode) -> bool:
        """Recursively verify node hashes"""
        if node.is_leaf():
            return True
        
        # Recompute hash and compare
        expected_hash = node._compute_hash()
        if node.hash != expected_hash:
            return False
        
        # Verify children
        if node.left and not self._verify_node(node.left):
            return False
        if node.right and not self._verify_node(node.right):
            return False
        
        return True
    
    def generate_proof(self, element: Any) -> List[Tuple[str, str]]:
        """
        Generate proof of inclusion for element
        
        Args:
            element: Element to prove inclusion for
            
        Returns:
            List of (side, hash) tuples representing proof path (bottom-up)
        """
        # Find element index
        index = None
        for i, leaf in enumerate(self.leaves):
            if leaf.data == element:
                index = i
                break
        
        if index is None:
            raise ValueError(f"Element {element} not found in tree")
            
        proof = []
        self._get_proof_recursive(self.root, index, proof)
        return proof

    def _get_proof_recursive(self, node: MerkleNode, target_idx: int, proof: List[Tuple[str, str]]):
        """
        Recursively generate proof
        
        Args:
            node: Current node
            target_idx: Global index of the target leaf (0-based)
            proof: List to append proof steps to
        """
        if node.is_leaf():
            return

        # Determine if target is in left or right subtree
        # The left subtree covers leaves [0, node.left.width) relative to this node's start
        # Since we don't pass 'start', we can just check if target_idx < node.left.width
        # But wait, target_idx is global. We need relative index or to decrement as we go right.
        
        # Actually, simpler: check if target index falls within left child's range
        # But we need to know the offset of 'node'. 
        # Easier: Pass relative index.
        
        left_width = node.left.width if node.left else 0
        
        if target_idx < left_width:
            # Target is in left subtree
            # Sibling is right
            if node.right:
                proof.insert(0, ('right', node.right.hash))
            self._get_proof_recursive(node.left, target_idx, proof)
        else:
            # Target is in right subtree
            # Sibling is left
            if node.left:
                proof.insert(0, ('left', node.left.hash))
            # Adjust index for right subtree
            self._get_proof_recursive(node.right, target_idx - left_width, proof)
    
    @staticmethod
    def verify_proof(root_hash: str, element: Any, proof: List[Tuple[str, str]]) -> bool:
        """
        Verify proof of inclusion
        
        Args:
            root_hash: Expected root hash
            element: Element being proved
            proof: Proof path from generate_proof
            
        Returns:
            True if proof is valid
        """
        # Start with element hash
        current_hash = hashlib.sha256(str(element).encode()).hexdigest()
        
        # Apply proof steps (proof is ordered bottom-up)
        for side, sibling_hash in proof:
            if side == 'left':
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root_hash
    
    def diff(self, other: 'MerkleTree') -> List[Tuple[int, Any, Any]]:
        """
        Find differences between two trees
        
        Args:
            other: Another Merkle tree to compare
            
        Returns:
            List of (index, self_data, other_data) for differences
        """
        if len(self.leaves) != len(other.leaves):
            raise ValueError("Trees must have same number of leaves")
        
        diffs = []
        self._diff_recursive(self.root, other.root, 0, diffs)
        return diffs
    
    def _diff_recursive(
        self,
        node1: MerkleNode,
        node2: MerkleNode,
        offset: int,
        diffs: List[Tuple[int, Any, Any]]
    ):
        """Recursively find differences between subtrees"""
        # Same hash = same subtree
        if node1.hash == node2.hash:
            return
        
        # If both are leaves, we found a diff
        if node1.is_leaf() and node2.is_leaf():
            diffs.append((offset, node1.data, node2.data))
            return
            
        # If one is leaf and other is not, structure mismatch (should not happen if size same)
        # Assuming identical structure for identical size
        
        # Recurse
        # Left child always exists for internal nodes
        if node1.left and node2.left:
            self._diff_recursive(node1.left, node2.left, offset, diffs)
            
        # Right child might not exist (if node was promoted)
        if node1.right and node2.right:
            left_width = node1.left.width
            self._diff_recursive(node1.right, node2.right, offset + left_width, diffs)
    
    def __repr__(self):
        return f"MerkleTree(leaves={len(self.leaves)}, root={self.root.hash[:8]}...)"


# Example usage
if __name__ == "__main__":
    print("=== Merkle Tree Example ===\n")
    
    # Create tree from data
    print("--- Building Tree ---")
    data = ["block1", "block2", "block3", "block4"]
    tree = MerkleTree(data)
    
    print(f"Tree: {tree}")
    print(f"Root hash: {tree.root_hash()}")
    print(f"Verified: {tree.verify()}")
    
    # Generate proof
    print("\n--- Proof of Inclusion ---")
    element = "block2"
    proof = tree.generate_proof(element)
    
    print(f"Proof for '{element}':")
    for side, hash_val in proof:
        print(f"  {side}: {hash_val[:16]}...")
    
    # Verify proof
    is_valid = MerkleTree.verify_proof(tree.root_hash(), element, proof)
    print(f"Proof valid: {is_valid}")
    
    # Compare trees
    print("\n--- Tree Comparison ---")
    tree1 = MerkleTree(["a", "b", "c", "d"])
    tree2 = MerkleTree(["a", "b", "X", "d"])  # Different
    
    print(f"Tree 1 root: {tree1.root_hash()[:16]}...")
    print(f"Tree 2 root: {tree2.root_hash()[:16]}...")
    
    diffs = tree1.diff(tree2)
    print(f"\nDifferences found: {len(diffs)}")
    for idx, val1, val2 in diffs:
        print(f"  Index {idx}: '{val1}' != '{val2}'")
    
    # Efficient sync
    print("\n--- Efficient Synchronization ---")
    # Only need to transfer different blocks
    print(f"Blocks to sync: {len(diffs)} out of {len(data)}")
    print(f"Efficiency: {(1 - len(diffs)/len(data)) * 100:.1f}% savings")