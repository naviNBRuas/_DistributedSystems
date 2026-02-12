"""
Consistent Hash Ring Implementation

Provides a distributed hash ring with virtual nodes for
uniform data distribution and minimal rebalancing.
Thread-safe implementation suitable for production use.
"""

import bisect
import hashlib
import logging
import threading
from typing import List, Dict, Optional, Callable, Tuple, Set, Any
from collections import defaultdict

# Configure null handler to avoid "No handler found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())


def default_hash_function(key: str) -> int:
    """Default hash function using MD5"""
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


class ConsistentHashRing:
    """
    Consistent hash ring with virtual nodes.
    
    Features:
    - Virtual nodes for uniform distribution
    - Minimal key redistribution on node changes
    - Configurable replication
    - Weighted nodes support
    - Thread-safe operations
    
    Time Complexity:
    - Lookup: O(log V) where V is virtual nodes
    - Add/Remove: O(V log V)
    """
    
    def __init__(
        self,
        nodes: Optional[List[str]] = None,
        virtual_nodes: int = 150,
        hash_function: Optional[Callable[[str], int]] = None,
        weights: Optional[Dict[str, int]] = None,
        node_metadata: Optional[Dict[str, dict]] = None
    ):
        """
        Initialize consistent hash ring.
        
        Args:
            nodes: List of physical node identifiers
            virtual_nodes: Number of virtual nodes per physical node
            hash_function: Custom hash function (str -> int)
            weights: Node weights {node_id: weight} for capacity
            node_metadata: Additional metadata per node
        """
        self.virtual_nodes_per_node = virtual_nodes
        self.hash_function = hash_function or default_hash_function
        self.weights = weights or {}
        self.node_metadata = node_metadata or {}
        
        # Ring: sorted list of (hash, node) tuples
        self.ring: List[Tuple[int, str]] = []
        
        # Reverse mapping: hash -> physical node
        self.hash_to_node: Dict[int, str] = {}
        
        # Track physical nodes
        self.nodes: Set[str] = set()
        
        # Thread safety
        self._lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
        
        # Add initial nodes
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def _get_virtual_node_count(self, node: str) -> int:
        """Get number of virtual nodes for a physical node"""
        weight = self.weights.get(node, 1)
        return int(self.virtual_nodes_per_node * weight)
    
    def add_node(self, node: str) -> None:
        """
        Add a node to the ring.
        
        Args:
            node: Node identifier to add
        """
        with self._lock:
            if node in self.nodes:
                self.logger.info("Node '%s' already exists in ring", node)
                return
            
            self.nodes.add(node)
            
            # Add virtual nodes
            virtual_count = self._get_virtual_node_count(node)
            
            for i in range(virtual_count):
                # Create unique identifier for virtual node
                virtual_key = f"{node}:{i}"
                hash_value = self.hash_function(virtual_key)
                
                # Add to ring
                bisect.insort(self.ring, (hash_value, node))
                self.hash_to_node[hash_value] = node
            
            self.logger.info("Added node '%s' (%d virtual nodes)", node, virtual_count)
    
    def remove_node(self, node: str) -> None:
        """
        Remove a node from the ring.
        
        Args:
            node: Node identifier to remove
        """
        with self._lock:
            if node not in self.nodes:
                self.logger.warning("Attempted to remove non-existent node '%s'", node)
                return
            
            self.nodes.remove(node)
            
            # Remove all virtual nodes for this physical node
            self.ring = [(h, n) for h, n in self.ring if n != node]
            
            # Clean up hash mapping
            self.hash_to_node = {h: n for h, n in self.ring}
            
            self.logger.info("Removed node '%s'", node)
    
    def get_node(self, key: str) -> Optional[str]:
        """
        Get the node responsible for a key.
        
        Args:
            key: Key to look up
            
        Returns:
            Node identifier, or None if ring is empty
        """
        with self._lock:
            if not self.ring:
                return None
            
            # Hash the key
            key_hash = self.hash_function(key)
            
            # Binary search for first node >= key_hash
            idx = bisect.bisect_right(self.ring, (key_hash, ''))
            
            # Wrap around if necessary
            if idx == len(self.ring):
                idx = 0
            
            return self.ring[idx][1]
    
    def get_nodes(self, key: str, count: int) -> List[str]:
        """
        Get multiple nodes for replication.
        
        Returns N successor nodes (clockwise on ring).
        
        Args:
            key: Key to look up
            count: Number of nodes to return
            
        Returns:
            List of unique node identifiers
        """
        with self._lock:
            if not self.ring or count <= 0:
                return []
            
            # Hash the key
            key_hash = self.hash_function(key)
            
            # Find starting position
            idx = bisect.bisect_right(self.ring, (key_hash, ''))
            
            # Collect unique nodes
            result = []
            seen = set()
            
            # Iterate through the ring to find distinct physical nodes
            # In a very large ring, limited to checking sufficient items to find 'count' unique nodes
            # or exhausting the ring once.
            ring_len = len(self.ring)
            for i in range(ring_len):
                pos = (idx + i) % ring_len
                node = self.ring[pos][1]
                
                if node not in seen:
                    result.append(node)
                    seen.add(node)
                    
                    if len(result) == count:
                        break
            
            return result
    
    def get_node_with_metadata(self, key: str) -> Tuple[Optional[str], dict]:
        """
        Get node and its metadata.
        
        Args:
            key: Key to look up
            
        Returns:
            (node_id, metadata) tuple. node_id is None if ring is empty.
        """
        with self._lock:
            node = self.get_node(key)
            if node is None:
                return None, {}
            metadata = self.node_metadata.get(node, {})
            return node, metadata
    
    def get_distribution_stats(self) -> Dict[str, Any]:
        """
        Analyze key distribution across nodes.
        
        Returns:
            Statistics dictionary with distribution metrics
        """
        with self._lock:
            if not self.ring:
                return {}
            
            # Count virtual nodes per physical node
            virtual_counts: Dict[str, int] = defaultdict(int)
            for _, node in self.ring:
                virtual_counts[node] += 1
            
            # Calculate statistics
            counts = list(virtual_counts.values())
            avg = sum(counts) / len(counts)
            variance = sum((c - avg) ** 2 for c in counts) / len(counts)
            std_dev = variance ** 0.5
            
            return {
                "total_virtual_nodes": len(self.ring),
                "physical_nodes": len(self.nodes),
                "virtual_per_node": dict(virtual_counts),
                "avg_virtual_per_node": avg,
                "std_dev": std_dev / avg if avg > 0 else 0,
                "min_virtual": min(counts),
                "max_virtual": max(counts)
            }
    
    def analyze_distribution(self, keys: List[str]) -> Dict[str, Any]:
        """
        Analyze how keys are distributed across nodes.
        
        Args:
            keys: List of keys to analyze
            
        Returns:
            Distribution statistics
        """
        # Note: We don't lock the entire method to allow concurrent reads during analysis,
        # but get_node is individually locked.
        node_counts: Dict[str, int] = defaultdict(int)
        
        for key in keys:
            node = self.get_node(key)
            if node:
                node_counts[node] += 1
        
        counts = list(node_counts.values())
        if not counts:
            return {}
        
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5
        
        return {
            "total_keys": len(keys),
            "keys_per_node": dict(node_counts),
            "avg_keys_per_node": avg,
            "std_dev": std_dev / avg if avg > 0 else 0,
            "min_keys": min(counts),
            "max_keys": max(counts),
            "balance_ratio": min(counts) / max(counts) if max(counts) > 0 else 0
        }
    
    def __repr__(self) -> str:
        with self._lock:
            return f"ConsistentHashRing(nodes={len(self.nodes)}, virtual_nodes={len(self.ring)})"


# Example usage
if __name__ == "__main__":
    # Configure logging for example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("=== Consistent Hash Ring Example ===\n")
    
    # Create ring with 3 nodes
    ring = ConsistentHashRing(
        nodes=["node1", "node2", "node3"],
        virtual_nodes=150
    )
    
    print(f"{ring}\n")
    
    # Test key distribution
    test_keys = [f"user:{i}" for i in range(100)]
    
    print("--- Key Distribution ---")
    stats = ring.analyze_distribution(test_keys)
    for node_id, count in stats.get("keys_per_node", {}).items():
        print(f"{node_id}: {count} keys ({count/stats['total_keys']*100:.1f}%)")
    
    if stats:
        print(f"\nBalance (std dev): {stats['std_dev']:.2%}")
        print(f"Min/Max ratio: {stats['balance_ratio']:.2f}")
    
    # Test replication
    print("\n--- Replication ---")
    test_key = "user:12345"
    replicas = ring.get_nodes(test_key, count=3)
    print(f"Key '{test_key}' replicas: {replicas}")
    
    # Add a node
    print("\n--- Adding Node ---")
    ring.add_node("node4")
    
    new_stats = ring.analyze_distribution(test_keys)
    print(f"After adding node4:")
    for node_id, count in new_stats.get("keys_per_node", {}).items():
        print(f"{node_id}: {count} keys ({count/new_stats['total_keys']*100:.1f}%)")
    
    print(f"\nNew distribution balance: {new_stats.get('std_dev', 0):.2%}")

