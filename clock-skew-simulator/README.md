# Clock Skew Simulator

A comprehensive toolkit for understanding and experimenting with time, causality, and clock synchronization in distributed systems through logical and hybrid clocks.

## Overview

This project provides implementations and interactive simulations of various clock mechanisms used in distributed systems to establish causality and ordering of events without relying on synchronized physical clocks.

**Version**: 0.1.0

## Features

- ✅ **Lamport Clocks** — Logical timestamps for total ordering
- ✅ **Vector Clocks** — Causal ordering and concurrent event detection
- ✅ **Hybrid Logical Clocks (HLC)** — Combines physical and logical time
- ✅ **Clock Skew Simulation** — Model clock drift and synchronization
- ✅ **Causality Visualization** — Interactive event graphs and happens-before relations
- ✅ **NTP Simulation** — Network Time Protocol behavior modeling

## Architecture

```
clock-skew-simulator/
├── src/
│   ├── lamport_clock.py       # Lamport logical clock
│   ├── vector_clock.py        # Vector clock implementation
│   ├── hybrid_clock.py        # Hybrid logical clock (HLC)
│   ├── physical_clock.py      # Physical clock with drift
│   ├── ntp_simulator.py       # NTP synchronization simulation
│   ├── causality.py           # Causality detection and analysis
│   └── visualizer.py          # Event graph visualization
├── examples/
│   ├── distributed_database.py    # Using clocks for consistency
│   ├── event_ordering.py          # Event ordering scenarios
│   └── clock_drift_demo.py        # Clock drift visualization
├── simulations/
│   ├── network_partition.py       # Partition scenarios
│   ├── clock_synchronization.py   # NTP simulation
│   └── concurrent_events.py       # Concurrency detection
├── tests/
│   ├── test_lamport.py
│   ├── test_vector_clock.py
│   └── test_causality.py
├── docs/
│   ├── THEORY.md              # Theory and background
│   ├── API.md
│   └── SCENARIOS.md
├── VERSION
└── requirements.txt
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

#### Lamport Clocks

```python
from lamport_clock import LamportClock

# Create clocks for different nodes
clock_a = LamportClock(node_id="A")
clock_b = LamportClock(node_id="B")

# Local event increments clock
clock_a.tick()  # A: 1

# Send message (includes timestamp)
timestamp = clock_a.send()  # A: 2

# Receive message (update clock)
clock_b.receive(timestamp)  # B: max(B_current, received) + 1 = 3
```

#### Vector Clocks

```python
from vector_clock import VectorClock

# Create vector clocks
clock_a = VectorClock(node_id="A", peers=["B", "C"])
clock_b = VectorClock(node_id="B", peers=["A", "C"])

# Local events
clock_a.tick()  # A: [1, 0, 0]
clock_b.tick()  # B: [0, 1, 0]

# Send/receive
timestamp = clock_a.send()  # A: [2, 0, 0]
clock_b.receive("A", timestamp)  # B: [2, 2, 0]

# Detect causality
if clock_a.happened_before(clock_b):
    print("A happened before B")
elif clock_a.concurrent_with(clock_b):
    print("A and B are concurrent")
```

#### Hybrid Logical Clocks

```python
from hybrid_clock import HybridLogicalClock

clock = HybridLogicalClock(node_id="node1")

# Get timestamp (combines physical and logical)
ts = clock.now()  # (physical_time, logical_counter)

# Send message
send_ts = clock.send()

# Receive message
clock.receive(send_ts)
```

## Clock Types

### 1. Lamport Clocks

**Purpose**: Establish total ordering of events

**Properties**:
- If event A happened before event B, then timestamp(A) < timestamp(B)
- Converse is not necessarily true
- Simple counter, easy to implement

**Use Cases**:
- Log ordering
- Event sequencing
- Distributed debugging

```python
# Example: Ordering distributed logs
log_a = clock_a.tick()  # "Event A at timestamp 5"
log_b = clock_b.tick()  # "Event B at timestamp 7"
# Can order: log_a < log_b
```

### 2. Vector Clocks

**Purpose**: Detect causality and concurrency

**Properties**:
- Can determine if events are causally related or concurrent
- Each node maintains a vector of logical clocks
- Size grows with number of nodes

**Use Cases**:
- Conflict detection in replicated databases
- Version vectors in distributed storage
- Debugging race conditions

```python
# Example: Detecting concurrent updates
if update_a.concurrent_with(update_b):
    # Conflict! Need resolution strategy
    resolve_conflict(update_a, update_b)
```

### 3. Hybrid Logical Clocks (HLC)

**Purpose**: Combine benefits of physical and logical time

**Properties**:
- Monotonically increasing
- Close to physical time
- Bounded logical component
- Causality tracking like vector clocks but compact

**Use Cases**:
- Distributed databases (e.g., CockroachDB, MongoDB)
- Consistent snapshots
- TTL and expiration

```python
# Example: Consistent snapshot
snapshot_time = hlc.now()
# Read all data with timestamps <= snapshot_time
```

## Causality and Happens-Before

### Happens-Before Relation (→)

Event A → Event B if:
1. A and B are on the same process and A comes before B
2. A is a send event and B is the corresponding receive
3. Transitive: A → B and B → C implies A → C

### Concurrent Events (||)

Events A and B are concurrent (A || B) if:
- NOT (A → B) AND NOT (B → A)

```python
from causality import CausalityAnalyzer

analyzer = CausalityAnalyzer()
analyzer.add_event("A", "send", timestamp_a)
analyzer.add_event("B", "receive", timestamp_b)

# Check causality
if analyzer.happens_before("A", "B"):
    print("A caused B")
elif analyzer.concurrent("A", "B"):
    print("A and B are concurrent")
```

## Clock Skew and Drift

### Physical Clock Simulation

```python
from physical_clock import PhysicalClock

# Create clock with drift
clock = PhysicalClock(
    node_id="node1",
    drift_rate=0.001,  # 0.1% faster/slower
    skew=0.5            # Initial 0.5 second offset
)

# Read clock (affected by drift)
time1 = clock.read()
# ... time passes ...
time2 = clock.read()

# Clock drifts over time
actual_elapsed = 10.0
measured_elapsed = time2 - time1  # May be 10.01 or 9.99
```

### Clock Synchronization

```python
from ntp_simulator import NTPSimulator

# Simulate NTP synchronization
ntp = NTPSimulator(
    nodes=["node1", "node2", "node3"],
    max_clock_skew=1.0,
    network_latency=0.01
)

# Run synchronization
ntp.synchronize()

# Check clock skew after sync
skew = ntp.get_max_skew()
print(f"Max skew after sync: {skew} seconds")
```

## Simulations

### Network Partition Scenario

```python
from simulations.network_partition import PartitionSimulation

# Simulate partition with clock skew
sim = PartitionSimulation(
    nodes=["A", "B", "C", "D"],
    partition=[["A", "B"], ["C", "D"]],  # Two partitions
    duration=30  # seconds
)

# Run simulation
results = sim.run()

# Analyze causality violations
violations = results.get_causality_violations()
```

### Concurrent Update Detection

```python
from simulations.concurrent_events import ConcurrentUpdateSimulation

# Simulate concurrent updates to replicated data
sim = ConcurrentUpdateSimulation(
    replicas=["R1", "R2", "R3"],
    update_rate=10,  # updates per second
    clock_type="vector"
)

results = sim.run(duration=60)
print(f"Concurrent updates detected: {results.conflicts}")
```

## Visualization

### Event Graph

```python
from visualizer import EventGraphVisualizer

viz = EventGraphVisualizer()

# Add events
viz.add_event("A", 1, "send")
viz.add_event("B", 2, "receive")
viz.add_event("C", 3, "local")

# Add causal relationships
viz.add_happens_before("A", "B")

# Generate graph
viz.render("event_graph.png")
```

### Clock Drift Over Time

```python
from visualizer import ClockDriftVisualizer

viz = ClockDriftVisualizer()

# Add clock readings
viz.add_reading("node1", timestamp=0, reading=1000.0)
viz.add_reading("node1", timestamp=10, reading=1010.1)  # Drifted
viz.add_reading("node2", timestamp=0, reading=1000.0)
viz.add_reading("node2", timestamp=10, reading=1009.9)  # Drifted

# Plot drift
viz.plot("clock_drift.png")
```

## Use Cases

### 1. Distributed Database Consistency

```python
from examples.distributed_database import ReplicatedDB

# Use vector clocks for versioning
db = ReplicatedDB(
    node_id="replica1",
    peers=["replica2", "replica3"],
    clock_type="vector"
)

# Write creates versioned entry
db.put("key1", "value1")  # Version: [1, 0, 0]

# Concurrent writes detected
db.put("key1", "value2")  # Version: [2, 0, 0]
# Another replica: db.put("key1", "value3")  # Version: [0, 1, 0]
# Conflict! Both versions retained
```

### 2. Event Ordering in Logs

```python
from examples.event_ordering import DistributedLogger

logger = DistributedLogger(clock_type="lamport")

# Log events across nodes
logger.log("node1", "User login")     # ts: 1
logger.log("node2", "Query database") # ts: 2
logger.log("node1", "Return result")  # ts: 3

# Events are totally ordered by timestamp
ordered_logs = logger.get_ordered_logs()
```

### 3. Detecting Concurrent Writes

```python
# Two nodes update the same key concurrently
vclock1 = VectorClock("node1", ["node2"])
vclock2 = VectorClock("node2", ["node1"])

# Independent updates
write1_ts = vclock1.tick()  # [1, 0]
write2_ts = vclock2.tick()  # [0, 1]

# Detect concurrency
if vclock1.concurrent_with(vclock2):
    print("Concurrent writes - conflict resolution needed")
```

## Performance Characteristics

| Clock Type | Space | Update Cost | Comparison Cost | Causality Detection |
|-----------|-------|-------------|-----------------|---------------------|
| Lamport   | O(1)  | O(1)        | O(1)            | Partial (one-way)   |
| Vector    | O(N)  | O(1)        | O(N)            | Complete            |
| HLC       | O(1)  | O(1)        | O(1)            | Complete (with msgs)|

Where N = number of nodes

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific simulation
python simulations/clock_synchronization.py

# Interactive scenarios
python examples/event_ordering.py --interactive
```

## Configuration

```python
from config import ClockConfig

config = ClockConfig(
    clock_type="hybrid",
    max_drift_rate=0.001,      # 0.1%
    sync_interval=60,           # seconds
    causality_tracking=True
)
```

## Integration Guide

### As a Submodule

```bash
git submodule add <repo-url>/clock-skew-simulator lib/clocks
```

### With Your Application

```python
# Add logical timestamps to your events
from lamport_clock import LamportClock

class EventProcessor:
    def __init__(self):
        self.clock = LamportClock(node_id="processor1")
    
    def process_event(self, event):
        timestamp = self.clock.tick()
        event.timestamp = timestamp
        # Process event...
```

## Educational Resources

See [docs/THEORY.md](./docs/THEORY.md) for:
- Clock synchronization theory
- Lamport's paper summary
- Vector clock algorithms
- HLC design rationale

## Examples

Complete examples in [examples/](./examples/):
- Distributed database with vector clocks
- Event ordering with Lamport clocks
- Clock drift visualization
- NTP simulation

## Dependencies

- Python 3.8+
- Optional: `matplotlib` for visualizations
- Optional: `networkx` for graph rendering

## Versioning

Current: **0.1.0**

Follows [Semantic Versioning](https://semver.org/)

## References

- [Time, Clocks, and the Ordering of Events in a Distributed System (Lamport, 1978)](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)
- [Vector Clocks](https://en.wikipedia.org/wiki/Vector_clock)
- [Hybrid Logical Clocks (Kulkarni et al., 2014)](https://cse.buffalo.edu/tech-reports/2014-04.pdf)
- [Network Time Protocol](https://www.ntp.org/)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=clock-skew-simulator
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration section above for `ClockConfig` settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
