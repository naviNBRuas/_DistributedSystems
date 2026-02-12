# Quorum Systems

Fault-tolerant coordination mechanisms using quorum-based replication for distributed data consistency.

## Overview

Quorum systems provide configurable trade-offs between consistency, availability, and performance in distributed storage. This project implements various quorum protocols including simple majorities, sloppy quorums, and read repair for building highly available datastores.

**Version**: 0.1.0

## Features

- ✅ **Simple Quorum (N/W/R)** — Read/write quorum configuration
- ✅ **Sloppy Quorums** — Availability over consistency
- ✅ **Read Repair** — Anti-entropy on reads
- ✅ **Hinted Handoff** — Temporary failover
- ✅ **Vector Clock Conflict Detection** — Concurrent write handling
- ✅ **Tunable Consistency** — ONE, QUORUM, ALL levels

## Architecture

```
quorum-systems/
├── src/
│   ├── quorum_coordinator.py  # Quorum coordination
│   ├── replica_manager.py     # Replica management
│   ├── read_repair.py         # Read repair mechanism
│   ├── hinted_handoff.py      # Hinted handoff
│   └── consistency_level.py   # Consistency levels
├── examples/
│   ├── distributed_kv.py      # Key-value store
│   ├── cassandra_style.py     # Cassandra-like quorum
│   └── dynamo_style.py        # DynamoDB-style quorum
├── tests/
│   ├── test_quorum.py
│   ├── test_availability.py
│   └── test_consistency.py
├── VERSION
└── requirements.txt
```

## Quick Start

### Basic Quorum Configuration

```python
from quorum_coordinator import QuorumCoordinator
from consistency_level import ConsistencyLevel

# Configure: N=3, W=2, R=2 (quorum)
coordinator = QuorumCoordinator(
    replicas=["node1", "node2", "node3"],
    write_quorum=2,
    read_quorum=2
)

# Write with quorum
coordinator.write(
    key="user:123",
    value={"name": "Alice"},
    consistency=ConsistencyLevel.QUORUM
)

# Read with quorum
value = coordinator.read(
    key="user:123",
    consistency=ConsistencyLevel.QUORUM
)
```

### Consistency Levels

```python
# ONE: Fastest, least consistent
value = coordinator.read(key, consistency=ConsistencyLevel.ONE)

# QUORUM: Balanced (default)
value = coordinator.read(key, consistency=ConsistencyLevel.QUORUM)

# ALL: Slowest, most consistent
value = coordinator.read(key, consistency=ConsistencyLevel.ALL)
```

## Quorum Protocols

### 1. Simple Quorum (N/W/R)

Classic quorum system:

```
N = Total replicas
W = Write quorum size
R = Read quorum size

Constraint: W + R > N (ensures overlap)
```

**Examples**:

```python
# Strong consistency: W + R > N
coordinator = QuorumCoordinator(
    replicas=5,
    write_quorum=3,  # W=3
    read_quorum=3    # R=3, W+R=6>5
)

# Read-optimized: low R, high W
coordinator = QuorumCoordinator(
    replicas=5,
    write_quorum=4,  # W=4
    read_quorum=2    # R=2, W+R=6>5
)

# Write-optimized: low W, high R
coordinator = QuorumCoordinator(
    replicas=5,
    write_quorum=2,  # W=2
    read_quorum=4    # R=4, W+R=6>5
)
```

### 2. Sloppy Quorums

Prioritize availability over strict consistency:

```python
from quorum_coordinator import SloppyQuorumCoordinator

# Use any W healthy nodes (not necessarily preference list)
coordinator = SloppyQuorumCoordinator(
    replicas=["A", "B", "C", "D", "E"],
    write_quorum=3,
    sloppy=True
)

# If node A is down, write to F instead (hinted handoff)
coordinator.write(key, value)
```

**Features**:
- Accept writes even if preferred nodes are down
- Store hints for unavailable nodes
- Deliver hints when nodes recover

### 3. Read Repair

Automatic anti-entropy during reads:

```python
from read_repair import ReadRepairCoordinator

coordinator = ReadRepairCoordinator(
    replicas=["node1", "node2", "node3"],
    read_quorum=2,
    read_repair=True  # Enable read repair
)

# Read triggers repair of stale replicas
value = coordinator.read(key="user:123")
# Behind the scenes:
# 1. Read from 2 replicas (quorum)
# 2. Detect version mismatch
# 3. Repair stale replica asynchronously
```

### 4. Hinted Handoff

Temporary storage for unavailable nodes:

```python
from hinted_handoff import HintedHandoff

handoff = HintedHandoff(storage_path="/var/hints")

# Node A is down, store hint
handoff.store_hint(
    target_node="A",
    key="user:123",
    value=data,
    timestamp=now()
)

# Node A recovers
if handoff.has_hints_for("A"):
    hints = handoff.retrieve_hints("A")
    for hint in hints:
        send_to_node("A", hint)
```

## Consistency Levels

### Available Levels

```python
class ConsistencyLevel(Enum):
    ONE = 1        # Wait for 1 replica
    TWO = 2        # Wait for 2 replicas
    THREE = 3      # Wait for 3 replicas
    QUORUM = "Q"   # Wait for (N/2 + 1)
    ALL = "ALL"    # Wait for all N replicas
    LOCAL_ONE = "L1"       # One in local datacenter
    LOCAL_QUORUM = "LQ"    # Quorum in local DC
```

### Usage

```python
# Fast reads, eventual consistency
value = kv_store.get(key, consistency=ConsistencyLevel.ONE)

# Balanced
value = kv_store.get(key, consistency=ConsistencyLevel.QUORUM)

# Strong consistency
value = kv_store.get(key, consistency=ConsistencyLevel.ALL)
```

## Implementation

### Quorum Write

```python
def write(self, key, value, consistency=ConsistencyLevel.QUORUM):
    """Write with quorum"""
    # Calculate required replicas
    required = self._get_required_count(consistency)
    
    # Send to all replicas
    futures = []
    for replica in self.replicas:
        future = self._send_write(replica, key, value)
        futures.append(future)
    
    # Wait for quorum
    successful = 0
    for future in futures:
        try:
            future.result(timeout=1.0)
            successful += 1
            
            if successful >= required:
                return True  # Quorum reached
        except TimeoutError:
            continue
    
    raise QuorumNotMetError(f"Only {successful}/{required} replicas")
```

### Quorum Read

```python
def read(self, key, consistency=ConsistencyLevel.QUORUM):
    """Read with quorum"""
    required = self._get_required_count(consistency)
    
    # Read from replicas
    responses = []
    for replica in self.replicas:
        try:
            value, version = self._send_read(replica, key)
            responses.append((value, version, replica))
            
            if len(responses) >= required:
                break  # Got quorum
        except:
            continue
    
    if len(responses) < required:
        raise QuorumNotMetError()
    
    # Resolve conflicts (pick latest version)
    latest = max(responses, key=lambda r: r[1])
    
    # Trigger read repair if needed
    if self.read_repair_enabled:
        self._async_read_repair(key, latest, responses)
    
    return latest[0]
```

## Use Cases

### 1. Distributed Key-Value Store

```python
class DistributedKV:
    def __init__(self, nodes, replication_factor=3):
        self.coordinator = QuorumCoordinator(
            replicas=nodes,
            write_quorum=2,
            read_quorum=2
        )
    
    def put(self, key, value):
        self.coordinator.write(key, value)
    
    def get(self, key):
        return self.coordinator.read(key)
```

### 2. Shopping Cart (High Availability)

```python
class ShoppingCart:
    def __init__(self):
        # Sloppy quorum: always available
        self.coordinator = SloppyQuorumCoordinator(
            replicas=5,
            write_quorum=2,  # Low W for fast writes
            read_quorum=2,
            sloppy=True
        )
    
    def add_item(self, cart_id, item):
        # Always succeed even if nodes down
        self.coordinator.write(
            f"cart:{cart_id}",
            item,
            consistency=ConsistencyLevel.ONE
        )
```

### 3. User Profile (Strong Consistency)

```python
class UserProfile:
    def __init__(self):
        self.coordinator = QuorumCoordinator(
            replicas=3,
            write_quorum=3,  # ALL writes
            read_quorum=1    # Fast reads
        )
    
    def update_profile(self, user_id, data):
        # Strong consistency
        self.coordinator.write(
            f"profile:{user_id}",
            data,
            consistency=ConsistencyLevel.ALL
        )
```

## CAP Theorem Trade-offs

### Configuration Guide

| N | W | R | Consistency | Availability | Use Case |
|---|---|---|-------------|--------------|----------|
| 3 | 2 | 2 | Strong | Medium | General purpose |
| 3 | 1 | 3 | Eventual | High | Read-heavy |
| 3 | 3 | 1 | Strong | Low | Write-heavy critical |
| 5 | 3 | 3 | Strong | Medium | High availability |
| 3 | 1 | 1 | Weak | Very High | Shopping cart |

### Consistency Equation

```
W + R > N  →  Strong consistency
W + R ≤ N  →  Eventual consistency
```

## Performance

### Latency

| Consistency | Latency (p50) | Latency (p99) |
|-------------|---------------|---------------|
| ONE | 1-5 ms | 10-20 ms |
| QUORUM | 5-15 ms | 30-50 ms |
| ALL | 10-30 ms | 50-100 ms |

### Availability

| Configuration | Tolerated Failures |
|---------------|-------------------|
| N=3, W=2, R=2 | 1 node |
| N=5, W=3, R=3 | 2 nodes |
| N=7, W=4, R=4 | 3 nodes |

## Monitoring

```python
# Get quorum statistics
stats = coordinator.get_stats()

print(f"Total reads: {stats['reads']}")
print(f"Quorum reads: {stats['quorum_reads']}")
print(f"Read repairs: {stats['read_repairs']}")
print(f"Hints pending: {stats['hints_pending']}")
print(f"Failed quorums: {stats['quorum_failures']}")
```

## Testing

```bash
# Run tests
python -m pytest tests/

# Availability tests
python tests/test_availability.py --kill-nodes 2

# Consistency tests
python tests/test_consistency.py --concurrent-writes 100
```

## Dependencies

- Python 3.8+
- No external dependencies (stdlib only)

## Versioning

Current: **0.1.0**

## References

- [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- [Cassandra: A Decentralized Structured Storage System](https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=quorum-systems
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration sections above for quorum settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
