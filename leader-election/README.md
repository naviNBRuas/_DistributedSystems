# Leader Election

Production-ready leader election algorithms for distributed coordination and preventing split-brain scenarios in clustered systems.

## Overview

This project provides multiple battle-tested leader election algorithms that enable distributed systems to coordinate and establish a single leader among a set of nodes, handling network failures and preventing split-brain scenarios.

**Version**: 0.1.0

## Features

- ✅ **Multiple Algorithms** — Bully, Ring, and Lease-based election
- ✅ **Split-Brain Prevention** — Quorum-based safety guarantees
- ✅ **Failure Detection** — Integrated heartbeat and timeout mechanisms
- ✅ **Dynamic Membership** — Handle node joins and failures
- ✅ **Fencing Tokens** — Prevent stale leader operations
- ✅ **Leader Leases** — Time-bounded leadership for safety

## Architecture

```
leader-election/
├── src/
│   ├── bully_algorithm.py     # Bully election algorithm
│   ├── ring_algorithm.py      # Ring-based election
│   ├── lease_based.py         # Lease-based coordination
│   ├── election_manager.py    # Unified election interface
│   ├── fencing.py             # Fencing tokens for safety
│   └── config.py              # Configuration
├── examples/
│   ├── master_worker.py       # Master-worker coordination
│   ├── singleton_service.py   # Singleton service pattern
│   └── split_brain_demo.py    # Split-brain prevention demo
├── tests/
│   ├── test_bully.py
│   ├── test_split_brain.py
│   └── test_failover.py
├── docs/
│   ├── ALGORITHMS.md
│   ├── API.md
│   └── PATTERNS.md
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
from election_manager import ElectionManager, Algorithm

# Create election manager
manager = ElectionManager(
    node_id="node1",
    peers=["node2", "node3", "node4", "node5"],
    algorithm=Algorithm.BULLY
)

# Start participating in elections
manager.start()

# Check if this node is the leader
if manager.is_leader():
    print("I am the leader!")
    # Perform leader duties
    
# Get current leader
leader_id = manager.get_leader()

# Register callback for leadership changes
def on_leadership_change(new_leader):
    print(f"New leader elected: {new_leader}")

manager.on_leader_change(on_leadership_change)
```

## Algorithms

### 1. Bully Algorithm

**Best for**: Small clusters with reliable ordering

The node with the highest ID becomes leader.

```python
from bully_algorithm import BullyElection

election = BullyElection(
    node_id="node3",
    peers=["node1", "node2", "node4", "node5"]
)
election.start_election()
```

**Characteristics**:
- **Time Complexity**: O(N²) messages in worst case
- **Convergence**: Fast (typically 2-3 message rounds)
- **Pros**: Simple, deterministic
- **Cons**: Not optimal for large clusters, requires reliable node IDs

**How it works**:
1. Node initiates election, sends ELECTION message to higher IDs
2. Higher nodes respond with OK and start their own election
3. If no OK received, node declares victory with COORDINATOR message
4. Highest surviving node becomes leader

### 2. Ring Algorithm

**Best for**: Medium clusters with token-passing pattern

Nodes organized in a logical ring, election message circulates.

```python
from ring_algorithm import RingElection

election = RingElection(
    node_id="node3",
    ring_order=["node1", "node2", "node3", "node4", "node5"]
)
election.start_election()
```

**Characteristics**:
- **Time Complexity**: O(N) messages
- **Convergence**: One complete ring traversal
- **Pros**: Fair, predictable message count
- **Cons**: Slower convergence, single point of failure in ring

**How it works**:
1. Node sends ELECTION message to next node in ring
2. Each node adds its ID to the message and forwards
3. When message completes ring, node with highest ID becomes leader
4. Leader sends ELECTED message around ring

### 3. Lease-Based

**Best for**: Production systems requiring strong safety

Time-bounded leadership with automatic expiration.

```python
from lease_based import LeaseBasedElection

election = LeaseBasedElection(
    node_id="node1",
    peers=["node2", "node3", "node4", "node5"],
    lease_duration=10,  # seconds
    quorum_size=3
)
election.start()
```

**Characteristics**:
- **Time Complexity**: O(N) for quorum
- **Convergence**: Fast with quorum
- **Pros**: Strong safety, prevents split-brain
- **Cons**: Requires reliable time synchronization

**How it works**:
1. Node requests leadership for a specific duration
2. Quorum of nodes must acknowledge the request
3. Leader must renew lease before expiration
4. If lease expires, new election automatically triggered

## Split-Brain Prevention

### Quorum-Based Safety

Requires majority quorum for leader election:

```python
election = LeaseBasedElection(
    node_id="node1",
    peers=["node2", "node3", "node4", "node5"],
    quorum_size=3  # Majority of 5 nodes
)
```

**Guarantees**:
- At most one leader in any partition
- Minority partition cannot elect leader
- Leader must maintain quorum to remain leader

### Fencing Tokens

Prevent stale leaders from performing operations:

```python
from fencing import FencingTokenManager

# Leader gets fencing token
token = manager.get_fencing_token()

# Perform operation with token
def perform_critical_operation():
    if token.is_valid():
        # Safe to proceed - we're the current leader
        execute_operation()
    else:
        # Token expired or we're no longer leader
        abort_operation()
```

**How it works**:
- Each leader epoch gets a monotonically increasing token
- Operations require valid token
- Stale leaders have invalid tokens, preventing split-brain operations

## Use Cases

### 1. Master-Worker Coordination

Single master coordinates multiple workers:

```python
from examples.master_worker import MasterWorker

mw = MasterWorker(node_id="node1", peers=["node2", "node3"])

if mw.is_master():
    # Assign work to workers
    mw.assign_task(worker_id="node2", task={"job": "process_batch_1"})
else:
    # Wait for tasks from master
    task = mw.receive_task()
```

### 2. Singleton Service

Ensure only one instance of a service runs:

```python
from examples.singleton_service import SingletonService

service = SingletonService(
    node_id="node1",
    peers=["node2", "node3"],
    service_factory=lambda: MyService()
)

service.start()
# Service runs only on leader node
```

### 3. Active-Passive Failover

Primary node handles traffic, standby takes over on failure:

```python
manager = ElectionManager(node_id="node1", peers=["node2"])

if manager.is_leader():
    # Handle traffic as primary
    server.start()
else:
    # Wait as standby
    manager.wait_for_leadership()
```

## Configuration

```python
from config import ElectionConfig

config = ElectionConfig(
    election_timeout=5000,      # milliseconds
    heartbeat_interval=1000,    # milliseconds  
    lease_duration=10,          # seconds
    quorum_size=3,              # nodes required for quorum
    max_election_rounds=10,     # prevent infinite elections
)
```

## API Reference

### ElectionManager

#### Methods

- `start()` — Start participating in elections
- `stop()` — Stop and step down if leader
- `is_leader() -> bool` — Check if this node is leader
- `get_leader() -> str` — Get current leader ID
- `trigger_election()` — Force a new election
- `get_fencing_token() -> FencingToken` — Get token for leader operations

#### Callbacks

- `on_leader_change(callback)` — Called when leadership changes
- `on_election_start(callback)` — Called when election begins
- `on_step_down(callback)` — Called when this node loses leadership

### FencingToken

- `is_valid() -> bool` — Check if token is still valid
- `get_epoch() -> int` — Get token epoch number
- `refresh()` — Refresh token (leader only)

## Failure Handling

### Leader Failure Detection

Leaders send periodic heartbeats:

```python
# Followers detect leader failure via missed heartbeats
if time_since_last_heartbeat > election_timeout:
    manager.trigger_election()
```

### Network Partitions

Quorum-based safety prevents multiple leaders:

```python
# Minority partition cannot elect leader
if len(reachable_peers) < quorum_size:
    # Cannot become leader
    state = FOLLOWER
```

### Simultaneous Elections

First election to complete wins:

```python
# Lower priority elections are aborted
if received_coordinator_message():
    abort_my_election()
```

## Performance Characteristics

| Algorithm | Election Time | Messages | Split-Brain Safe |
|-----------|---------------|----------|------------------|
| Bully     | O(N²)         | O(N²)    | No (without quorum) |
| Ring      | O(N)          | O(N)     | No (without quorum) |
| Lease     | O(N)          | O(N)     | Yes (with quorum) |

## Testing

```bash
# Unit tests
python -m pytest tests/

# Simulate network partition
python tests/test_split_brain.py --partition-time 30

# Stress test elections
python tests/test_failover.py --failures 10 --nodes 5
```

## Production Considerations

### 1. Time Synchronization

For lease-based elections:
- Use NTP or equivalent
- Monitor clock skew
- Set lease duration >> max clock skew

### 2. Network Reliability

- Monitor heartbeat failures
- Tune election timeout for network latency
- Use TCP for reliability (vs UDP)

### 3. Quorum Size

For N nodes:
- Quorum = floor(N/2) + 1
- Always use odd cluster sizes (3, 5, 7)
- 3 nodes: tolerates 1 failure
- 5 nodes: tolerates 2 failures

### 4. Monitoring

Track these metrics:
```python
metrics = manager.get_metrics()
# {
#   "elections_started": 5,
#   "elections_won": 2,
#   "leadership_duration": 3600,  # seconds
#   "heartbeat_failures": 3
# }
```

## Integration Guide

### As a Submodule

```bash
git submodule add <repo-url>/leader-election lib/leader-election
```

### With Service Discovery

```python
# Integrate with service discovery
peers = service_discovery.get_peers()
manager = ElectionManager(node_id=my_id, peers=peers)
```

### With Distributed Locks

```python
# Use leader election for lock acquisition
if manager.is_leader():
    # Implicit lock - I'm the only leader
    perform_exclusive_operation()
```

## Examples

See [examples/](./examples/) for complete examples:
- Master-worker coordination
- Singleton service pattern
- Active-passive failover
- Split-brain prevention

## Dependencies

- Python 3.8+
- Standard library only

## Versioning

Current: **0.1.0**

Follows [Semantic Versioning](https://semver.org/)

## References

- [Distributed Leader Election](https://en.wikipedia.org/wiki/Leader_election)
- [The Bully Algorithm](https://en.wikipedia.org/wiki/Bully_algorithm)
- [Lease-Based Leader Election](https://martinfowler.com/articles/patterns-of-distributed-systems/lease.html)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=leader-election
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration section above for `ElectionConfig` settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
