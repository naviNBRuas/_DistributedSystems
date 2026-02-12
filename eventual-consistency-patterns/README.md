# Eventual Consistency Patterns

Practical patterns for building eventually consistent distributed systems.

## Overview

Eventual consistency allows systems to achieve high availability and performance while ensuring all replicas converge to the same state. This project provides battle-tested patterns and anti-entropy mechanisms.

**Version**: 0.1.0

## Features

- ✅ **Read Repair** — Fix inconsistencies during reads
- ✅ **Anti-Entropy** — Periodic reconciliation
- ✅ **Conflict Resolution** — LWW, vector clocks, CRDTs
- ✅ **Causal Consistency** — Preserve causality

## Quick Start

```python
from eventual_consistency import ReadRepair

repair = ReadRepair(replicas=["node1", "node2", "node3"])

# Read with repair
value = repair.read(key="user:123")
# Automatically repairs stale replicas in background
```

## Patterns

### 1. Read Repair

```python
def read_with_repair(key):
    # Read from multiple replicas
    values = [replica.get(key) for replica in replicas]
    
    # Pick latest version
    latest = max(values, key=lambda v: v.timestamp)
    
    # Repair stale replicas asynchronously
    for replica, value in zip(replicas, values):
        if value.timestamp < latest.timestamp:
            repair_replica(replica, key, latest)
    
    return latest
```

### 2. Anti-Entropy (Merkle Tree Sync)

```python
from anti_entropy import MerkleSync

sync = MerkleSync()

# Periodic reconciliation
while True:
    for peer in peers:
        diffs = sync.compare_trees(peer)
        sync.repair_differences(peer, diffs)
    
    time.sleep(300)  # Every 5 minutes
```

### 3. Conflict Resolution

```python
# Last-Write-Wins
def resolve_lww(v1, v2):
    return v1 if v1.timestamp > v2.timestamp else v2

# Vector Clock
def resolve_vector_clock(v1, v2):
    if v1.vector_clock.happens_before(v2.vector_clock):
        return v2
    elif v2.vector_clock.happens_before(v1.vector_clock):
        return v1
    else:
        # Concurrent - application-specific resolution
        return merge_concurrent(v1, v2)
```

## Consistency Models

- **Strong consistency**: All reads see latest write
- **Eventual consistency**: All replicas converge eventually
- **Causal consistency**: Causally related operations ordered
- **Read-your-writes**: See your own writes

## Use Cases

- Shopping carts
- Social media feeds
- Collaborative editing
- Distributed caches

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=eventual-consistency-patterns
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
