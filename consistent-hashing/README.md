# Consistent Hashing

Production-grade consistent hashing implementation for distributed data partitioning, load balancing, and minimal data movement during cluster resizing.

## Overview

Consistent hashing is a distributed hashing technique that minimizes data reorganization when nodes are added or removed from a cluster. This implementation provides virtual nodes, custom hash functions, and replication strategies.

**Version**: 0.1.0

## Features

- ✅ **Virtual Nodes** — Uniform load distribution across physical nodes
- ✅ **Minimal Redistribution** — Only K/N keys move when nodes change
- ✅ **Pluggable Hash Functions** — MD5, SHA1, MurmurHash, custom
- ✅ **Replication Support** — Configurable replication factor
- ✅ **Weighted Nodes** — Assign more virtual nodes to powerful servers
- ✅ **Ring Visualization** — Debug and understand key distribution

## Architecture

```
consistent-hashing/
├── src/
│   ├── consistent_hash.py     # Main consistent hash ring
│   ├── hash_functions.py      # Hash function implementations
│   ├── virtual_nodes.py       # Virtual node management
│   └── replication.py         # Replication strategies
├── examples/
│   ├── distributed_cache.py   # Cache partitioning
│   ├── data_sharding.py       # Database sharding
│   └── load_balancer.py       # Request routing
├── tests/
│   ├── test_distribution.py
│   ├── test_rebalancing.py
│   └── test_replication.py
├── VERSION
└── requirements.txt
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from consistent_hash import ConsistentHashRing

# Create hash ring with 3 nodes
ring = ConsistentHashRing(
    nodes=["node1", "node2", "node3"],
    virtual_nodes=150  # Virtual nodes per physical node
)

# Find which node should store a key
node = ring.get_node("user:12345")
print(f"Key belongs to: {node}")  # e.g., "node2"

# Add a new node (minimal redistribution)
ring.add_node("node4")

# Remove a node
ring.remove_node("node2")

# Get multiple nodes for replication
replicas = ring.get_nodes("user:12345", count=3)
print(f"Replicas: {replicas}")  # e.g., ["node1", "node3", "node4"]
```

## Use Cases

### 1. Distributed Cache Partitioning

```python
class DistributedCache:
    def __init__(self, cache_nodes):
        self.ring = ConsistentHashRing(nodes=cache_nodes)
        self.caches = {node: {} for node in cache_nodes}
    
    def set(self, key, value):
        node = self.ring.get_node(key)
        self.caches[node][key] = value
    
    def get(self, key):
        node = self.ring.get_node(key)
        return self.caches[node].get(key)
```

### 2. Database Sharding

```python
class ShardedDatabase:
    def __init__(self, db_shards):
        self.ring = ConsistentHashRing(nodes=db_shards, virtual_nodes=200)
    
    def get_shard(self, user_id):
        return self.ring.get_node(f"user:{user_id}")
    
    def insert_user(self, user_id, data):
        shard = self.get_shard(user_id)
        # Insert into specific shard
```

### 3. Load Balancing

```python
class LoadBalancer:
    def __init__(self, servers, weights=None):
        self.ring = ConsistentHashRing(nodes=servers, weights=weights)
    
    def route_request(self, request_id):
        server = self.ring.get_node(request_id)
        # Route to selected server
        return server
```

## Virtual Nodes

Virtual nodes ensure uniform distribution even with a small number of physical nodes:

```python
# Without virtual nodes (poor distribution)
ring = ConsistentHashRing(nodes=["node1", "node2"], virtual_nodes=1)

# With virtual nodes (better distribution)
ring = ConsistentHashRing(nodes=["node1", "node2"], virtual_nodes=150)

# Analyze distribution
stats = ring.get_distribution_stats()
print(f"Standard deviation: {stats['std_dev']:.2%}")
```

### Why Virtual Nodes?

- **Uniform distribution**: More points on ring = better balance
- **Smooth rebalancing**: Keys distributed across many virtual nodes
- **Handles heterogeneous nodes**: Weighted virtual nodes for different capacity

## Weighted Nodes

Assign more capacity to powerful servers:

```python
# node1 gets 2x the load of node2 and node3
ring = ConsistentHashRing(
    nodes=["node1", "node2", "node3"],
    weights={"node1": 2, "node2": 1, "node3": 1},
    virtual_nodes=150
)
```

## Replication

Store data on multiple nodes for fault tolerance:

```python
# Get N replicas (clockwise successor nodes)
replicas = ring.get_nodes("user:12345", count=3)

# Store on all replicas
for node in replicas:
    store_on_node(node, key, value)
```

## Hash Functions

### Built-in Functions

```python
from hash_functions import md5_hash, sha1_hash, murmur3_hash

# Use different hash function
ring = ConsistentHashRing(
    nodes=["node1", "node2", "node3"],
    hash_function=murmur3_hash  # Faster than MD5
)
```

### Custom Hash Function

```python
def custom_hash(key: str) -> int:
    # Must return integer in range [0, 2^32)
    return hash(key) & 0xFFFFFFFF

ring = ConsistentHashRing(
    nodes=["node1", "node2"],
    hash_function=custom_hash
)
```

## Rebalancing

When nodes are added/removed, only affected keys need to move:

```python
# Initial state
ring = ConsistentHashRing(nodes=["node1", "node2", "node3"])

# Track which keys would move
keys_to_move = ring.get_affected_keys_on_add("node4")

# Add node
ring.add_node("node4")

# Expected: Only ~25% of keys move (1/4 of ring)
print(f"Keys to redistribute: {len(keys_to_move)}")
```

### Rebalancing Metrics

```python
# Analyze impact of adding/removing nodes
impact = ring.analyze_node_change(
    action="add",
    node="node4"
)

print(f"Affected keys: {impact['affected_percentage']:.1%}")
print(f"Keys per node: {impact['keys_per_node']}")
```

## Distribution Statistics

Verify uniform distribution:

```python
# Generate test keys
test_keys = [f"key:{i}" for i in range(10000)]

# Check distribution
stats = ring.analyze_distribution(test_keys)

print(f"Keys per node: {stats['keys_per_node']}")
print(f"Standard deviation: {stats['std_dev']:.2%}")
print(f"Min/Max ratio: {stats['balance_ratio']:.2f}")

# Ideal: std_dev < 5%, balance_ratio close to 1.0
```

## Advanced Features

### Custom Node Metadata

```python
# Store metadata with nodes
ring = ConsistentHashRing(
    nodes=["node1", "node2"],
    node_metadata={
        "node1": {"datacenter": "us-east", "capacity": 100},
        "node2": {"datacenter": "us-west", "capacity": 200}
    }
)

node, metadata = ring.get_node_with_metadata("key")
print(f"Datacenter: {metadata['datacenter']}")
```

### Availability Zones

```python
# Ensure replicas in different zones
ring = ConsistentHashRing(
    nodes=["node1", "node2", "node3"],
    zones={"node1": "az1", "node2": "az2", "node3": "az1"}
)

# Get replicas in different zones
replicas = ring.get_nodes_diverse("key", count=2, zone_diverse=True)
```

## Performance Characteristics

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| Lookup    | O(log V)       | O(V)            |
| Add Node  | O(V log V)     | O(V)            |
| Remove    | O(V log V)     | O(V)            |

Where V = number of virtual nodes

### Optimization Tips

1. **Virtual Nodes**: 100-200 per physical node is good balance
2. **Hash Function**: MurmurHash3 faster than MD5/SHA1
3. **Caching**: Cache node lookups for hot keys
4. **Batch Operations**: Add/remove multiple nodes together

## Testing

```bash
# Run tests
python -m pytest tests/

# Distribution analysis
python examples/analyze_distribution.py --nodes 10 --keys 100000

# Rebalancing simulation
python examples/rebalance_simulation.py
```

## Integration Examples

### Redis Cluster Simulation

```python
class RedisCluster:
    def __init__(self, redis_instances):
        self.ring = ConsistentHashRing(
            nodes=redis_instances,
            virtual_nodes=150
        )
        self.clients = {node: redis.Redis(node) for node in redis_instances}
    
    def set(self, key, value):
        node = self.ring.get_node(key)
        self.clients[node].set(key, value)
    
    def get(self, key):
        node = self.ring.get_node(key)
        return self.clients[node].get(key)
```

### DynamoDB-style Partitioning

```python
class DynamoPartitioner:
    def __init__(self, nodes, replication_factor=3):
        self.ring = ConsistentHashRing(nodes=nodes)
        self.replication_factor = replication_factor
    
    def get_coordinators(self, partition_key):
        # Get N replicas for quorum writes
        return self.ring.get_nodes(partition_key, count=self.replication_factor)
    
    def write(self, partition_key, data, W=2):
        coordinators = self.get_coordinators(partition_key)
        # Write to W coordinators
```

## Comparison with Alternatives

### vs Modulo Hashing

```python
# Modulo: N % num_nodes (moves ~100% on resize)
node = nodes[hash(key) % len(nodes)]

# Consistent Hashing: moves ~1/N keys
node = ring.get_node(key)
```

### vs Rendezvous Hashing

- **Consistent Hashing**: Better for dynamic clusters
- **Rendezvous**: Better for static clusters, simpler

## Dependencies

- Python 3.8+
- Optional: `mmh3` for MurmurHash3

## Versioning

Current: **0.1.0**

## References

- [Consistent Hashing and Random Trees](https://www.akamai.com/us/en/multimedia/documents/technical-publication/consistent-hashing-and-random-trees-distributed-caching-protocols-for-relieving-hot-spots-on-the-world-wide-web-technical-publication.pdf)
- [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- [Consistent Hashing (Wikipedia)](https://en.wikipedia.org/wiki/Consistent_hashing)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=consistent-hashing
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
