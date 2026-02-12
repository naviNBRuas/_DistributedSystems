import hashlib
from typing import Dict, List, Tuple, Optional
from .models import VersionedValue

class MerkleTree:
    """
    Bucket-based Merkle Tree for Anti-Entropy.
    Stable against insertions/deletions.
    """
    def __init__(self, data: Dict[str, VersionedValue] = None, num_buckets: int = 16):
        self.num_buckets = num_buckets
        self.buckets: Dict[int, List[Tuple[str, str]]] = {i: [] for i in range(num_buckets)}
        self.bucket_hashes: Dict[int, str] = {}
        self.tree: Dict[int, str] = {} # Map node_index -> hash. Root is 1.
        
        if data:
            self.build(data)

    def _hash_key(self, key: str) -> int:
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16) % self.num_buckets

    def _hash_val(self, val: VersionedValue) -> str:
        s = f"{val.timestamp}:{val.value}"
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def build(self, data: Dict[str, VersionedValue]):
        # 1. Assign to buckets
        for key, val in data.items():
            b_idx = self._hash_key(key)
            self.buckets[b_idx].append((key, self._hash_val(val)))

        # 2. Hash buckets
        for i in range(self.num_buckets):
            # Sort by key to ensure deterministic order
            self.buckets[i].sort(key=lambda x: x[0])
            
            hasher = hashlib.sha256()
            for key, val_hash in self.buckets[i]:
                hasher.update(f"{key}:{val_hash}".encode('utf-8'))
            self.bucket_hashes[i] = hasher.hexdigest()

        # 3. Build Tree (Binary Heap style: 1 is root, 2*i is left, 2*i+1 is right)
        # Leaves are at indices [num_buckets, 2*num_buckets - 1] if num_buckets is power of 2
        # Let's assume num_buckets is power of 2 for simplicity (16 default)
        
        # Place leaves
        for i in range(self.num_buckets):
            node_idx = self.num_buckets + i
            self.tree[node_idx] = self.bucket_hashes[i]

        # Build up
        for i in range(self.num_buckets - 1, 0, -1):
            left = self.tree.get(2 * i, "")
            right = self.tree.get(2 * i + 1, "")
            self.tree[i] = hashlib.sha256((left + right).encode('utf-8')).hexdigest()

    def get_root_hash(self) -> str:
        return self.tree.get(1, "")

class MerkleSync:
    def compare_trees(self, local: MerkleTree, remote: MerkleTree) -> List[str]:
        """
        Compare local and remote trees.
        Returns list of keys belonging to divergent buckets.
        """
        if local.num_buckets != remote.num_buckets:
            raise ValueError("Cannot compare trees with different bucket counts")

        diff_keys = []
        self._compare_recursive(1, local, remote, diff_keys)
        return diff_keys

    def _compare_recursive(self, node_idx: int, local: MerkleTree, remote: MerkleTree, diff_keys: List[str]):
        local_hash = local.tree.get(node_idx, "")
        remote_hash = remote.tree.get(node_idx, "")

        if local_hash == remote_hash:
            return

        # If leaf (bucket level)
        if node_idx >= local.num_buckets:
            bucket_idx = node_idx - local.num_buckets
            # Add all keys from this bucket (from both sides) to diff_keys
            # This is a broad sync strategy: if bucket differs, check all keys in bucket.
            local_keys = [k for k, _ in local.buckets[bucket_idx]]
            remote_keys = [k for k, _ in remote.buckets[bucket_idx]]
            
            # Use set union
            diff_keys.extend(list(set(local_keys) | set(remote_keys)))
            return

        # Internal node, recurse
        self._compare_recursive(2 * node_idx, local, remote, diff_keys)
        self._compare_recursive(2 * node_idx + 1, local, remote, diff_keys)