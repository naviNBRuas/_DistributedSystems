# Gossip Protocol

A production-ready implementation of epidemic-style gossip protocols for decentralized state propagation in distributed systems.

## Overview

This project provides efficient, fault-tolerant gossip protocols for disseminating information across large-scale distributed systems. Gossip protocols enable eventually consistent state sharing without centralized coordination.

**Version**: 0.1.0

## Features

- ✅ **Push Gossip** — Nodes actively push updates to random peers
- ✅ **Pull Gossip** — Nodes actively pull updates from random peers  
- ✅ **Push-Pull Hybrid** — Combines both for faster convergence
- ✅ **Anti-Entropy** — Periodic full state reconciliation
- ✅ **Failure Detection** — Integrated phi-accrual failure detector
- ✅ **Membership Management** — Dynamic join/leave with SWIM protocol
- ✅ **Configurable Fanout** — Tune convergence speed vs bandwidth

## Architecture

```
gossip-protocol/
├── src/
│   ├── gossip_node.py        # Core gossip node implementation
│   ├── membership.py          # Cluster membership management (SWIM)
│   ├── failure_detector.py   # Phi-accrual failure detection
│   ├── message.py             # Gossip message types
│   ├── state_store.py         # Versioned state storage (vector clocks)
│   └── config.py              # Configuration
├── examples/
│   ├── distributed_cache.py   # Distributed cache example
│   ├── service_discovery.py   # Service discovery system
│   └── event_bus.py           # Pub/sub event bus
├── tests/
│   ├── test_convergence.py
│   ├── test_failure_detection.py
│   └── test_membership.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── TUNING.md
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
from gossip_node import GossipNode

# Create a gossip node
node = GossipNode(
    node_id="node1",
    bind_address="127.0.0.1:5001",
    seed_nodes=["127.0.0.1:5002", "127.0.0.1:5003"]
)

# Start the node
node.start()

# Update local state (will be gossiped to cluster)
node.set("service:api", {"host": "10.0.1.5", "port": 8080, "status": "healthy"})

# Read eventually consistent state
value = node.get("service:api")

# Subscribe to state changes
def on_update(key, value):
    print(f"Key {key} updated to {value}")

node.subscribe("service:*", on_update)
```

## Use Cases

### 1. Service Discovery

```python
# Nodes gossip service endpoints
node.set("service:users", {"host": "10.0.1.5", "port": 8080})
node.set("service:orders", {"host": "10.0.1.6", "port": 8081})

# All nodes eventually see all services
services = node.get_prefix("service:")
```

### 2. Distributed Cache

```python
# Cache entries propagate via gossip
cache.set("user:123", user_data, ttl=300)

# Reads hit local state (eventually consistent)
user = cache.get("user:123")
```

### 3. Cluster Metadata

```python
# Share configuration across cluster
node.set("config:max_connections", 1000)
node.set("config:timeout", 30)

# All nodes see the same configuration
config = node.get_prefix("config:")
```

## Protocol Details

### Push Gossip

1. Node updates local state
2. Every gossip interval, select random peers (fanout)
3. Send state updates to selected peers
4. Peers merge received updates

**Pros**: Fast for new updates  
**Cons**: May not reach all nodes if updates stop

### Pull Gossip

1. Every gossip interval, select random peers
2. Request their state digests
3. Request full state for missing/stale entries

**Pros**: Eventually reaches all nodes  
**Cons**: Slower for new updates

### Push-Pull (Recommended)

Combines both approaches for optimal convergence:
- Push for fast initial propagation
- Pull for anti-entropy and completeness

## Configuration

```python
config = {
    "gossip_interval": 1000,      # milliseconds between gossip rounds
    "gossip_fanout": 3,            # number of peers to gossip with
    "membership_gossip_interval": 500,  # SWIM membership updates
    "failure_detection_interval": 1000,
    "suspicion_timeout": 5000,    # time before marking node as failed
    "max_transmission_count": 3,   # anti-entropy retransmission
}
```

## Performance Characteristics

- **Convergence Time**: O(log N) gossip rounds to reach all nodes
- **Message Complexity**: O(N log N) messages total
- **Bandwidth**: Configurable via fanout (higher = faster + more bandwidth)
- **Fault Tolerance**: Tolerates up to N-1 failures (eventual recovery)

## Failure Detection

Uses **Phi-accrual failure detector** for adaptive failure detection:
- Continuously adapts to network conditions
- No hard timeouts (uses statistical likelihood)
- Low false positive rate in variable networks

```python
# Check if a node is suspected as failed
if node.is_failed("node2"):
    print("Node2 is likely down")

# Get failure probability
phi = node.get_failure_phi("node2")  # Higher = more likely failed
```

## Membership Management

Implements SWIM (Scalable Weakly-consistent Infection-style Membership):
- Nodes join by contacting seed nodes
- Periodic ping-req for indirect probing
- Graceful leave vs failure detection
- Suspicion mechanism to reduce false positives

```python
# Join cluster
node.join(seed_nodes=["127.0.0.1:5001"])

# Get current members
members = node.get_members()

# Leave gracefully
node.leave()
```

## State Semantics

### Consistency Model

- **Eventually consistent**: All nodes converge to the same state
- **Conflict resolution**: Last-write-wins with vector clocks
- **Causality tracking**: Vector clocks for happens-before relationships

### State Operations

```python
# Set with metadata
node.set("key", "value", metadata={"version": 1, "ttl": 300})

# Conditional update (CAS)
success = node.compare_and_set("key", old_value, new_value)

# Delete with tombstone
node.delete("key")  # Propagates deletion marker
```

## Integration Guide

### As a Submodule

```bash
git submodule add <repo-url>/gossip-protocol lib/gossip
```

### Network Transport

Default uses UDP multicast. Pluggable transports:

```python
from transport import TCPTransport, UDPTransport

node = GossipNode(
    node_id="node1",
    transport=TCPTransport()  # Or custom transport
)
```

### State Store Backend

Default uses in-memory store. Pluggable backends:

```python
from state_store import RedisStateStore

node = GossipNode(
    node_id="node1",
    state_store=RedisStateStore(redis_url="redis://localhost:6379")
)
```

## Testing

```bash
# Unit tests
python -m pytest tests/

# Convergence simulation
python tests/test_convergence.py --nodes 100 --failures 10

# Partition testing
python tests/test_partition.py --partition-duration 30
```

## Tuning Guide

### For Low Latency

- Increase gossip_fanout (more bandwidth, faster convergence)
- Decrease gossip_interval (more CPU, faster updates)

### For Large Clusters

- Keep fanout low (3-5) for bandwidth efficiency
- Increase gossip_interval slightly
- Use push-pull to ensure convergence

### For Unreliable Networks

- Increase max_transmission_count
- Tune failure detector threshold (phi)
- Consider using TCP transport

See [TUNING.md](./docs/TUNING.md) for detailed guidance.

## Monitoring

Expose metrics for observability:

```python
metrics = node.get_metrics()
# {
#   "gossip_rounds": 1523,
#   "messages_sent": 4569,
#   "messages_received": 4432,
#   "state_size": 256,
#   "cluster_size": 10,
#   "suspected_failures": 0
# }
```

## Production Considerations

1. **Bandwidth**: Monitor and limit gossip traffic in large clusters
2. **State Size**: Implement TTL and garbage collection for stale state
3. **Convergence**: Monitor convergence time as cluster grows
4. **Security**: Add encryption and authentication for production use

## Examples

See [examples/](./examples/) for complete examples:
- Distributed cache with gossip
- Service discovery system
- Event bus with pub/sub

## Dependencies

- Python 3.8+
- Optional: `msgpack` for efficient serialization

## Versioning

Current: **0.1.0**

Follows [Semantic Versioning](https://semver.org/)

## References

- [Epidemic Algorithms for Replicated Database Maintenance](https://dl.acm.org/doi/10.1145/41840.41841)
- [SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol](https://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf)
- [The Phi Accrual Failure Detector](https://pdfs.semanticscholar.org/11ae/4c0c0d0c36dc177c1fff5eb84fa49aa3e1a8.pdf)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=gossip-protocol
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration section above for gossip settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
