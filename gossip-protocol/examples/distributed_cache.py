"""
Example: Distributed Cache using Gossip Protocol

This example shows how to build a distributed cache where
cache entries propagate via gossip to all nodes in the cluster.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gossip_node import GossipNode


class DistributedCache:
    """
    Distributed cache with eventual consistency via gossip
    
    Cache entries are stored locally and propagated to all nodes.
    Reads are always local (fast), writes propagate eventually.
    """
    
    def __init__(self, node_id: str, bind_address: str, seed_nodes: list[str] = None):
        self.node = GossipNode(
            node_id=node_id,
            bind_address=bind_address,
            seed_nodes=seed_nodes,
            gossip_interval=1000,  # 1 second
            gossip_fanout=3
        )
        self.node.start()
    
    def set(self, key: str, value: any, ttl: int = None):
        """
        Set a cache entry
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        metadata = {}
        if ttl:
            metadata['ttl'] = ttl
            metadata['expires_at'] = time.time() + ttl
        
        cache_key = f"cache:{key}"
        self.node.set(cache_key, value, metadata)
    
    def get(self, key: str) -> any:
        """
        Get a cache entry
        
        Returns the locally cached value (eventually consistent)
        """
        cache_key = f"cache:{key}"
        return self.node.get(cache_key)
    
    def delete(self, key: str):
        """Delete a cache entry"""
        cache_key = f"cache:{key}"
        self.node.delete(cache_key)
    
    def on_cache_change(self, callback):
        """Subscribe to cache changes"""
        self.node.subscribe("cache:*", callback)
    
    def get_stats(self):
        """Get cache statistics"""
        metrics = self.node.get_metrics()
        return {
            "cached_items": metrics["state_size"],
            "cluster_size": metrics["cluster_size"],
            "gossip_rounds": metrics["gossip_rounds"]
        }
    
    def stop(self):
        """Stop the cache node"""
        self.node.stop()


def main():
    """Example usage of distributed cache"""
    
    # Create a 3-node cache cluster
    cache1 = DistributedCache("cache1", "127.0.0.1:5001")
    cache2 = DistributedCache("cache2", "127.0.0.1:5002", seed_nodes=["127.0.0.1:5001"])
    cache3 = DistributedCache("cache3", "127.0.0.1:5003", seed_nodes=["127.0.0.1:5001"])
    
    # Set values on different nodes
    print("\n=== Setting cache entries ===")
    cache1.set("user:123", {"name": "Alice", "email": "alice@example.com"})
    cache2.set("user:456", {"name": "Bob", "email": "bob@example.com"})
    cache3.set("product:789", {"name": "Widget", "price": 29.99})
    
    # Wait for gossip propagation
    print("\nWaiting for gossip propagation...")
    time.sleep(3)
    
    # Read from different nodes (should see all entries)
    print("\n=== Reading from all nodes ===")
    print(f"Cache1 sees user:123: {cache1.get('user:123')}")
    print(f"Cache1 sees user:456: {cache1.get('user:456')}")
    print(f"Cache2 sees product:789: {cache2.get('product:789')}")
    print(f"Cache3 sees user:123: {cache3.get('user:123')}")
    
    # Show statistics
    print("\n=== Cache Statistics ===")
    print(f"Cache1: {cache1.get_stats()}")
    print(f"Cache2: {cache2.get_stats()}")
    print(f"Cache3: {cache3.get_stats()}")
    
    # Cleanup
    cache1.stop()
    cache2.stop()
    cache3.stop()


if __name__ == "__main__":
    main()
