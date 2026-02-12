# Raft Consensus from Scratch

A production-grade implementation of the Raft consensus algorithm built from first principles, designed as a reusable component for distributed systems.

## Overview

This project provides a complete, standalone implementation of the [Raft consensus algorithm](https://raft.github.io/), suitable for building consistent distributed databases, replicated state machines, and coordination services.

**Version**: 0.1.0

## Features

- ✅ **Leader Election** — Randomized timeouts, term-based voting, split-brain prevention
- ✅ **Log Replication** — Ordered, durable append-only logs with consistency guarantees
- ✅ **Safety Guarantees** — Leader completeness, log matching, state machine safety
- ✅ **Membership Changes** — Dynamic cluster reconfiguration (joint consensus)
- ✅ **Log Compaction** — Snapshotting to prevent unbounded log growth
- ✅ **Persistence** — Durable state across crashes

## Architecture

```
raft-from-scratch/
├── src/
│   ├── raft_node.py          # Core Raft node implementation
│   ├── log.py                # Replicated log management
│   ├── state_machine.py      # State machine interface
│   ├── rpc.py                # RPC handlers (AppendEntries, RequestVote)
│   ├── storage.py            # Persistent storage layer
│   └── config.py             # Configuration and constants
├── examples/
│   ├── kv_store.py           # Key-value store example
│   └── distributed_counter.py
├── tests/
│   ├── test_leader_election.py
│   ├── test_log_replication.py
│   └── test_membership_change.py
├── docs/
│   ├── ARCHITECTURE.md       # Detailed design decisions
│   ├── API.md                # Public API documentation
│   └── INTEGRATION.md        # Integration guide
├── VERSION                   # Semantic version
└── requirements.txt
```

## Quick Start

### Installation

```bash
# As a dependency
pip install -r requirements.txt

# Copy into your project
cp -r raft-from-scratch/ /path/to/your/project/
```

### Basic Usage

```python
from raft_node import RaftNode
from state_machine import KeyValueStateMachine

# Create a Raft node
node = RaftNode(
    node_id="node1",
    peers=["node2", "node3", "node4", "node5"],
    state_machine=KeyValueStateMachine(),
    storage_path="/var/raft/node1"
)

# Start the node
node.start()

# Submit a command (only succeeds on leader)
result = node.submit_command({"op": "set", "key": "foo", "value": "bar"})

# Read from state machine (linearizable reads)
value = node.read_state("foo")
```

## Integration Guide

### As a Submodule

```bash
git submodule add <repo-url>/raft-from-scratch lib/raft
```

### Interface Requirements

Implement the `StateMachine` interface for your domain:

```python
class StateMachine(ABC):
    @abstractmethod
    def apply(self, command: dict) -> Any:
        """Apply a committed command to the state machine"""
        pass
    
    @abstractmethod
    def snapshot(self) -> bytes:
        """Create a snapshot of current state"""
        pass
    
    @abstractmethod
    def restore(self, snapshot: bytes) -> None:
        """Restore state from snapshot"""
        pass
```

### Configuration

```python
config = {
    "election_timeout_min": 150,  # milliseconds
    "election_timeout_max": 300,
    "heartbeat_interval": 50,
    "max_log_entries_per_request": 100,
    "snapshot_interval": 10000,  # entries
}
```

## API Reference

### RaftNode

#### Methods

- `start()` — Start the Raft node
- `stop()` — Gracefully shutdown the node
- `submit_command(cmd: dict) -> Future` — Submit a command for consensus
- `read_state(key: str) -> Any` — Linearizable read from state machine
- `add_peer(peer_id: str)` — Add a new node to the cluster
- `remove_peer(peer_id: str)` — Remove a node from the cluster

#### Properties

- `is_leader: bool` — Whether this node is the current leader
- `current_term: int` — Current election term
- `commit_index: int` — Index of highest committed log entry
- `state: NodeState` — Current node state (FOLLOWER, CANDIDATE, LEADER)

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests with network failures
python -m pytest tests/integration/ --chaos

# Benchmark
python benchmarks/throughput_test.py
```

## Design Decisions

### Why Raft?

- **Understandability** — Easier to reason about than Paxos
- **Proven** — Used in production systems (etcd, Consul, CockroachDB)
- **Complete** — Well-specified algorithm with formal verification

### Implementation Choices

1. **Single-threaded per node** — Simplifies reasoning, uses async I/O
2. **Pluggable storage** — Support for memory, disk, or custom backends
3. **Explicit timeouts** — Configurable for different network conditions
4. **No wire protocol assumptions** — Bring your own RPC (gRPC, HTTP, TCP)

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed rationale.

## Performance Characteristics

- **Writes**: Linearizable, require majority quorum (2F+1 for F failures)
- **Reads**: Linearizable (requires leader lease or read index protocol)
- **Latency**: ~1-2 RTTs for commit in normal operation
- **Throughput**: Scales with batching (10K+ ops/sec with batching)

## Fault Tolerance

- **Node failures**: Tolerates F failures in a 2F+1 cluster
- **Network partitions**: Minority partition cannot commit (safety preserved)
- **Leader failure**: Automatic election of new leader
- **Byzantine failures**: Not handled (use BFT algorithm instead)

## Production Considerations

### Monitoring

The node exposes metrics for:
- Leader election frequency
- Log replication lag
- Commit latency
- Heartbeat failures

### Tuning

- Adjust election timeouts based on network latency
- Configure snapshot interval based on log growth rate
- Size your cluster (3 nodes for dev, 5 for prod, 7 for geo-distributed)

### Operational Best Practices

1. Always use persistent storage in production
2. Monitor leader stability (frequent elections indicate issues)
3. Use odd cluster sizes (3, 5, 7) for quorum math
4. Plan for rolling upgrades (membership change protocol)

## Examples

### Key-Value Store

```python
# See examples/kv_store.py
from examples.kv_store import RaftKVStore

store = RaftKVStore(node_id="node1", peers=["node2", "node3"])
store.set("user:123", {"name": "Alice", "email": "founder@nbr.company"})
user = store.get("user:123")
```

### Distributed Lock

```python
# See examples/distributed_lock.py
from examples.distributed_lock import RaftLock

lock = RaftLock(node_id="node1", peers=["node2", "node3"])
with lock.acquire("resource:abc", timeout=30):
    # Critical section - only one client can be here
    perform_exclusive_operation()
```

## Dependencies

- Python 3.8+
- No external runtime dependencies (stdlib only)
- Optional: `msgpack` for efficient serialization

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Current: **0.1.0**

## References

- [In Search of an Understandable Consensus Algorithm (Raft Paper)](https://raft.github.io/raft.pdf)
- [Raft Visualization](https://raft.github.io/)
- [TLA+ Specification](https://github.com/ongardie/raft.tla)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=raft-from-scratch
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration section above for Raft settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
