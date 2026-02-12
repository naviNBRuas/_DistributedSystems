# Merkle Trees

Cryptographic hash trees for efficient data synchronization, verification, and anti-entropy in distributed systems.

## Overview

Merkle trees (hash trees) enable efficient comparison and synchronization of large datasets by organizing data into a tree where each node contains a cryptographic hash of its children. This project provides production implementations for data integrity, replication, and distributed system reconciliation.

**Version**: 0.1.0

## Features

- ✅ **Binary Merkle Tree** — Classic binary hash tree
- ✅ **Efficient Diff Detection** — O(log N) comparison
- ✅ **Anti-Entropy** — Identify divergent subtrees
- ✅ **Proof of Inclusion** — Verify element membership
- ✅ **Range Queries** — Query arbitrary data ranges
- ✅ **Incremental Updates** — Add/remove without full rebuild

## Architecture

```
merkle-trees/
├── src/
│   ├── merkle_tree.py         # Core Merkle tree
│   ├── merkle_proof.py        # Inclusion proofs
│   ├── anti_entropy.py        # Synchronization protocol
│   └── range_tree.py          # Range query support
├── examples/
│   ├── data_sync.py           # Database synchronization
│   ├── file_verification.py  # File integrity
│   └── blockchain_lite.py     # Simplified blockchain
├── tests/
│   ├── test_merkle_tree.py
│   ├── test_proof.py
│   └── test_sync.py
├── VERSION
└── requirements.txt
```

## Quick Start

### Basic Merkle Tree

```python
from merkle_tree import MerkleTree

# Create tree from data
data = ["block1", "block2", "block3", "block4"]
tree = MerkleTree(data)

# Get root hash
root = tree.root_hash()
print(f"Root: {root}")

# Verify tree integrity
assert tree.verify()
```

### Efficient Diff Detection

```python
# Tree 1
tree1 = MerkleTree(["a", "b", "c", "d"])

# Tree 2 (slightly different)
tree2 = MerkleTree(["a", "b", "X", "d"])  # 'c' changed to 'X'

# Find differences
diffs = tree1.diff(tree2)
print(f"Different subtrees: {diffs}")  # [(2, 'c'), (2, 'X')]
```

## Core Concepts

### 1. Hash Tree Structure

```
         Root Hash
        /          \
    Hash(A,B)    Hash(C,D)
     /    \       /    \
   H(A)  H(B)  H(C)  H(D)
    |     |     |     |
    A     B     C     D
```

**Properties**:
- Each leaf = hash of data block
- Each internal node = hash of children
- Root = hash of entire dataset

### 2. Efficient Comparison

Compare O(log N) hashes instead of N data blocks:

```python
def compare_trees(tree1, tree2, node1=None, node2=None):
    """Compare trees recursively"""
    if node1.hash == node2.hash:
        return []  # Subtrees identical
    
    if node1.is_leaf():
        return [(node1.data, node2.data)]  # Difference found
    
    # Recurse on children
    diffs = []
    diffs.extend(compare_trees(tree1, tree2, node1.left, node2.left))
    diffs.extend(compare_trees(tree1, tree2, node1.right, node2.right))
    return diffs
```

### 3. Proof of Inclusion

Prove element exists in tree with O(log N) proof:

```python
from merkle_proof import MerkleProof

# Create proof
proof = tree.generate_proof("block2")

# Verify proof
is_valid = proof.verify(
    root_hash=tree.root_hash(),
    element="block2"
)
```

## Use Cases

### 1. Database Synchronization

```python
class DatabaseSync:
    def __init__(self, db):
        self.db = db
        self.tree = None
    
    def build_tree(self):
        """Build Merkle tree from database"""
        rows = self.db.query("SELECT id, hash FROM records ORDER BY id")
        self.tree = MerkleTree([row.hash for row in rows])
    
    def sync_with(self, remote):
        """Synchronize with remote database"""
        # Compare root hashes
        if self.tree.root_hash() == remote.tree.root_hash():
            return  # Already synchronized
        
        # Find divergent ranges
        diffs = self.tree.diff(remote.tree)
        
        # Fetch only different blocks
        for index, _ in diffs:
            block = remote.fetch_block(index)
            self.db.update(block)
```

### 2. File Verification

```python
class FileVerifier:
    def __init__(self, file_path, block_size=4096):
        self.file_path = file_path
        self.block_size = block_size
        self.tree = self._build_tree()
    
    def _build_tree(self):
        """Build Merkle tree from file blocks"""
        blocks = []
        with open(self.file_path, 'rb') as f:
            while True:
                block = f.read(self.block_size)
                if not block:
                    break
                blocks.append(block)
        return MerkleTree(blocks)
    
    def verify_file(self, expected_root):
        """Verify file integrity"""
        return self.tree.root_hash() == expected_root
    
    def find_corrupted_blocks(self, other_tree):
        """Find which blocks are corrupted"""
        return self.tree.diff(other_tree)
```

### 3. Anti-Entropy Protocol

```python
class AntiEntropy:
    """Periodic reconciliation between replicas"""
    
    def __init__(self, node):
        self.node = node
        self.tree = None
    
    def build_tree(self):
        """Build Merkle tree from local data"""
        data = self.node.get_all_data()
        self.tree = MerkleTree(data)
    
    def reconcile(self, peer):
        """Find and repair differences with peer"""
        # Exchange root hashes
        local_root = self.tree.root_hash()
        remote_root = peer.get_root_hash()
        
        if local_root == remote_root:
            return  # No differences
        
        # Exchange subtree hashes recursively
        diffs = self._find_diffs(peer, self.tree.root, [])
        
        # Repair differences
        for path in diffs:
            data = peer.fetch_data(path)
            self.node.update_data(path, data)
    
    def _find_diffs(self, peer, node, path):
        """Recursively find divergent subtrees"""
        remote_hash = peer.get_hash(path)
        
        if node.hash == remote_hash:
            return []  # Subtree identical
        
        if node.is_leaf():
            return [path]  # Leaf differs
        
        # Recurse on children
        diffs = []
        diffs.extend(self._find_diffs(peer, node.left, path + [0]))
        diffs.extend(self._find_diffs(peer, node.right, path + [1]))
        return diffs
```

## Implementation

### MerkleTree Class

```python
import hashlib

class MerkleNode:
    def __init__(self, data=None, left=None, right=None):
        self.data = data
        self.left = left
        self.right = right
        self.hash = self._compute_hash()
    
    def _compute_hash(self):
        if self.is_leaf():
            # Leaf: hash of data
            return hashlib.sha256(self.data.encode()).hexdigest()
        else:
            # Internal: hash of children
            combined = self.left.hash + self.right.hash
            return hashlib.sha256(combined.encode()).hexdigest()
    
    def is_leaf(self):
        return self.left is None and self.right is None

class MerkleTree:
    def __init__(self, data_blocks):
        self.leaves = [MerkleNode(data=block) for block in data_blocks]
        self.root = self._build_tree(self.leaves)
    
    def _build_tree(self, nodes):
        """Build tree bottom-up"""
        if len(nodes) == 1:
            return nodes[0]
        
        # Pair nodes and create parents
        parents = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i+1] if i+1 < len(nodes) else nodes[i]  # Duplicate last
            parent = MerkleNode(left=left, right=right)
            parents.append(parent)
        
        return self._build_tree(parents)
    
    def root_hash(self):
        return self.root.hash
```

## Proof of Inclusion

### Generate Proof

```python
def generate_proof(self, element):
    """Generate proof for element"""
    # Find leaf index
    index = None
    for i, leaf in enumerate(self.leaves):
        if leaf.data == element:
            index = i
            break
    
    if index is None:
        raise ValueError("Element not in tree")
    
    # Collect sibling hashes along path
    proof = []
    current_index = index
    current_level = self.leaves[:]
    
    while len(current_level) > 1:
        # Get sibling
        if current_index % 2 == 0:
            # Left child, sibling is right
            sibling_index = current_index + 1
            side = 'right'
        else:
            # Right child, sibling is left
            sibling_index = current_index - 1
            side = 'left'
        
        if sibling_index < len(current_level):
            sibling_hash = current_level[sibling_index].hash
            proof.append((side, sibling_hash))
        
        # Move up to parent level
        current_index = current_index // 2
        current_level = self._get_parent_level(current_level)
    
    return proof
```

### Verify Proof

```python
def verify_proof(root_hash, element, proof):
    """Verify proof of inclusion"""
    # Start with element hash
    current_hash = hashlib.sha256(element.encode()).hexdigest()
    
    # Apply proof steps
    for side, sibling_hash in proof:
        if side == 'left':
            combined = sibling_hash + current_hash
        else:
            combined = current_hash + sibling_hash
        
        current_hash = hashlib.sha256(combined.encode()).hexdigest()
    
    # Check if computed root matches
    return current_hash == root_hash
```

## Performance

### Complexity

| Operation | Time | Space |
|-----------|------|-------|
| Build tree | O(N) | O(N) |
| Root hash | O(1) | - |
| Generate proof | O(log N) | O(log N) |
| Verify proof | O(log N) | O(log N) |
| Find diffs | O(D log N) | O(D) |

Where:
- N = number of elements
- D = number of differences

### Optimization Tips

1. **Balance tree**: Keep tree balanced for optimal height
2. **Cache hashes**: Avoid recomputing unchanged subtrees
3. **Batch updates**: Group changes before rebuilding
4. **Parallel hashing**: Compute hashes in parallel

## Comparison

### vs Full Scan

| Aspect | Merkle Tree | Full Scan |
|--------|-------------|-----------|
| Comparison | O(log N) | O(N) |
| Bandwidth | O(D log N) | O(N) |
| Use case | Large datasets | Small datasets |

### vs Bloom Filters

| Aspect | Merkle Tree | Bloom Filter |
|--------|-------------|--------------|
| False positives | No | Yes |
| Localize diffs | Yes | No |
| Space | O(N) | O(M) |

## Testing

```bash
# Run tests
python -m pytest tests/

# Benchmark
python tests/benchmark.py --size 1000000
```

## Dependencies

- Python 3.8+
- hashlib (stdlib)

## Versioning

Current: **0.1.0**

## References

- [Merkle, Ralph C. (1988). "A Digital Signature Based on a Conventional Encryption Function"](https://people.eecs.berkeley.edu/~raluca/cs261-f15/readings/merkle.pdf)
- [Bitcoin's Use of Merkle Trees](https://en.bitcoin.it/wiki/Protocol_documentation#Merkle_Trees)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=merkle-trees
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
No mandatory configuration. Optional settings are documented in the package code and examples.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
