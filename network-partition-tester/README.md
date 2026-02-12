# Network Partition Tester

A comprehensive toolkit for controlled network failure simulation, partition injection, and chaos engineering in distributed systems.

## Overview

This project provides tools and frameworks for testing distributed system resilience by simulating various network failures including partitions, latency, packet loss, and node failures in a controlled, reproducible manner.

**Version**: 0.1.0

## Features

- ✅ **Network Partitions** — Split cluster into isolated groups
- ✅ **Latency Injection** — Add configurable network delays
- ✅ **Packet Loss** — Simulate unreliable networks
- ✅ **Node Failures** — Controlled node crash and recovery
- ✅ **Asymmetric Partitions** — One-way communication failures
- ✅ **Partition Healing** — Automatic or manual partition recovery
- ✅ **Scenario Recording** — Record and replay failure scenarios
- ✅ **Assertion Framework** — Verify system behavior under failures

## Architecture

```
network-partition-tester/
├── src/
│   ├── partition_coordinator.py   # Main partition controller
│   ├── network_proxy.py           # Network traffic interceptor
│   ├── latency_injector.py        # Latency simulation
│   ├── packet_dropper.py          # Packet loss simulation
│   ├── failure_scenarios.py       # Pre-defined failure scenarios
│   ├── assertions.py              # Test assertions
│   └── recorder.py                # Scenario recording
├── examples/
│   ├── split_brain_test.py        # Test split-brain handling
│   ├── partition_tolerance.py     # CAP theorem demonstrations
│   └── healing_test.py            # Partition healing scenarios
├── scenarios/
│   ├── simple_partition.yaml      # Configuration files
│   ├── network_isolation.yaml
│   └── asymmetric_partition.yaml
├── tests/
│   ├── test_partition.py
│   ├── test_latency.py
│   └── test_assertions.py
├── docs/
│   ├── SCENARIOS.md
│   ├── API.md
│   └── CHAOS_ENGINEERING.md
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
from partition_coordinator import PartitionCoordinator
from network_proxy import NetworkProxy

# Create coordinator
coordinator = PartitionCoordinator(
    nodes=["node1", "node2", "node3", "node4", "node5"]
)

# Create a partition: split into two groups
coordinator.create_partition(
    groups=[["node1", "node2"], ["node3", "node4", "node5"]],
    duration=30  # seconds
)

# Nodes in different groups cannot communicate
# Wait for partition duration...

# Heal partition (reconnect all nodes)
coordinator.heal_partition()

# Verify system recovered
coordinator.assert_cluster_healthy()
```

## Failure Scenarios

### 1. Simple Partition

Split cluster into two equal groups:

```python
from failure_scenarios import SimplePartition

scenario = SimplePartition(
    nodes=["node1", "node2", "node3", "node4", "node5"],
    partition_sizes=[2, 3],
    duration=60
)

scenario.execute()

# Assertions
scenario.assert_minority_cannot_elect_leader()
scenario.assert_majority_continues_operating()
```

### 2. Network Isolation

Isolate a single node from the cluster:

```python
from failure_scenarios import NodeIsolation

scenario = NodeIsolation(
    nodes=["node1", "node2", "node3"],
    isolated_node="node2",
    duration=30
)

scenario.execute()

# Verify isolated node detected as failed
scenario.assert_node_marked_as_failed("node2")
```

### 3. Asymmetric Partition

One-way communication failure:

```python
from failure_scenarios import AsymmetricPartition

# node1 can send to node2, but node2 cannot send to node1
scenario = AsymmetricPartition(
    nodes=["node1", "node2"],
    blocked_direction=("node2", "node1"),
    duration=45
)

scenario.execute()
```

### 4. Cascading Failures

Multiple nodes fail sequentially:

```python
from failure_scenarios import CascadingFailures

scenario = CascadingFailures(
    nodes=["node1", "node2", "node3", "node4", "node5"],
    failure_sequence=[
        {"node": "node5", "delay": 0},
        {"node": "node4", "delay": 10},
        {"node": "node3", "delay": 20}
    ]
)

scenario.execute()
```

## Latency Injection

### Add Network Delays

```python
from latency_injector import LatencyInjector

injector = LatencyInjector()

# Add 100ms latency between node1 and node2
injector.add_latency(
    source="node1",
    target="node2",
    latency_ms=100,
    jitter_ms=10  # ±10ms variance
)

# Variable latency based on message size
injector.add_latency(
    source="node1",
    target="node2",
    latency_fn=lambda msg_size: msg_size / 1000  # 1ms per KB
)
```

### Network Congestion Simulation

```python
# Simulate network congestion
injector.simulate_congestion(
    nodes=["node1", "node2", "node3"],
    base_latency_ms=50,
    peak_latency_ms=500,
    duration=60
)
```

## Packet Loss

### Simulate Unreliable Networks

```python
from packet_dropper import PacketDropper

dropper = PacketDropper()

# Drop 10% of packets between nodes
dropper.set_loss_rate(
    source="node1",
    target="node2",
    loss_rate=0.1  # 10%
)

# Drop packets based on condition
dropper.drop_if(
    condition=lambda msg: msg.type == "HEARTBEAT",
    rate=0.5  # Drop 50% of heartbeats
)
```

### Burst Loss

```python
# Simulate burst packet loss
dropper.burst_loss(
    source="node1",
    target="node2",
    burst_duration=5,  # seconds
    loss_rate=1.0      # 100% loss during burst
)
```

## Node Failures

### Controlled Crashes

```python
from partition_coordinator import PartitionCoordinator

coordinator = PartitionCoordinator(nodes=["node1", "node2", "node3"])

# Crash a node (stops responding to all messages)
coordinator.crash_node("node2")

# Wait for failure detection...
time.sleep(10)

# Recover node
coordinator.recover_node("node2")
```

### Slow/Unresponsive Nodes

```python
# Make node respond slowly (but not crash)
coordinator.slow_node(
    node="node2",
    response_delay_ms=5000  # 5 second delay
)
```

## Partition Healing

### Automatic Healing

```python
# Partition heals after duration
coordinator.create_partition(
    groups=[["node1"], ["node2", "node3"]],
    duration=30,
    auto_heal=True  # Automatically heal after 30 seconds
)
```

### Manual Healing

```python
# Create partition without auto-heal
partition_id = coordinator.create_partition(
    groups=[["node1"], ["node2", "node3"]],
    auto_heal=False
)

# Heal when ready
coordinator.heal_partition(partition_id)
```

### Gradual Healing

```python
# Heal one node at a time
coordinator.gradual_heal(
    partition_id=partition_id,
    heal_interval=10  # Add one node every 10 seconds
)
```

## Assertion Framework

### Built-in Assertions

```python
from assertions import ClusterAssertions

assertions = ClusterAssertions(coordinator)

# Verify cluster properties
assertions.assert_exactly_one_leader()
assertions.assert_all_nodes_agree_on_leader()
assertions.assert_no_split_brain()
assertions.assert_data_consistency()
assertions.assert_availability(min_nodes=3)

# Verify partition behavior
assertions.assert_minority_partition_read_only()
assertions.assert_majority_partition_accepts_writes()

# Verify recovery
assertions.assert_partition_healed(timeout=60)
assertions.assert_cluster_converged()
```

### Custom Assertions

```python
def assert_custom_invariant():
    """Custom assertion for your system"""
    # Check system-specific invariant
    if not my_system.check_invariant():
        raise AssertionError("Invariant violated!")

# Register custom assertion
assertions.register(assert_custom_invariant)
```

## Scenario Configuration

### YAML Configuration

```yaml
# scenarios/split_brain_test.yaml
name: "Split Brain Test"
description: "Verify system prevents split-brain"

cluster:
  nodes: ["node1", "node2", "node3", "node4", "node5"]
  
partitions:
  - groups:
      - ["node1", "node2"]
      - ["node3", "node4", "node5"]
    duration: 60
    auto_heal: true
    
assertions:
  - type: "no_split_brain"
  - type: "exactly_one_leader"
  - type: "minority_read_only"
```

### Load and Execute

```python
from partition_coordinator import load_scenario

# Load scenario from YAML
scenario = load_scenario("scenarios/split_brain_test.yaml")

# Execute
results = scenario.execute()

# Check results
if results.all_assertions_passed():
    print("✓ All assertions passed")
else:
    print("✗ Failures:", results.get_failures())
```

## Recording and Replay

### Record Scenarios

```python
from recorder import ScenarioRecorder

recorder = ScenarioRecorder()

# Start recording
recorder.start("my_test")

# Perform operations (automatically recorded)
coordinator.create_partition(...)
coordinator.inject_latency(...)

# Stop recording
recorder.stop()

# Save scenario
recorder.save("recorded_scenarios/my_test.yaml")
```

### Replay Scenarios

```python
from recorder import ScenarioReplayer

replayer = ScenarioReplayer()

# Replay recorded scenario
replayer.load("recorded_scenarios/my_test.yaml")
replayer.replay()
```

## Integration with Testing Frameworks

### pytest Integration

```python
import pytest
from partition_coordinator import PartitionCoordinator

@pytest.fixture
def coordinator():
    c = PartitionCoordinator(nodes=["node1", "node2", "node3"])
    yield c
    c.cleanup()

def test_partition_tolerance(coordinator):
    """Test system tolerates network partition"""
    # Create partition
    coordinator.create_partition([["node1"], ["node2", "node3"]])
    
    # Verify behavior
    assert coordinator.get_leader() in ["node2", "node3"]
    
    # Heal and verify recovery
    coordinator.heal_partition()
    coordinator.assert_cluster_healthy()
```

### Continuous Testing

```python
# Run chaos tests continuously in production
from chaos_runner import ContinuousChaosRunner

runner = ContinuousChaosRunner(
    scenarios=["split_brain", "node_failure", "network_latency"],
    interval=3600,  # Run every hour
    max_disruption_time=300  # Max 5 minutes disruption
)

runner.start()
```

## CAP Theorem Demonstrations

### Partition Tolerance vs Availability

```python
from examples.partition_tolerance import CAPDemo

demo = CAPDemo(nodes=["node1", "node2", "node3"])

# Demonstrate CP (Consistency + Partition tolerance)
demo.demonstrate_cp()
# Result: Minority partition becomes unavailable

# Demonstrate AP (Availability + Partition tolerance)
demo.demonstrate_ap()
# Result: Both partitions remain available, eventual consistency
```

## Monitoring and Metrics

```python
# Get partition metrics
metrics = coordinator.get_metrics()

print(f"Total partitions created: {metrics.total_partitions}")
print(f"Average partition duration: {metrics.avg_duration}")
print(f"Packets dropped: {metrics.packets_dropped}")
print(f"Average latency added: {metrics.avg_latency_ms}ms")

# Export metrics for monitoring systems
coordinator.export_metrics("prometheus")
```

## Best Practices

### 1. Start Simple

Begin with simple partitions before complex scenarios:
```python
# Simple 2-partition split
coordinator.create_partition([["node1"], ["node2", "node3"]])
```

### 2. Use Timeouts

Always set timeouts to prevent infinite waits:
```python
coordinator.assert_cluster_healthy(timeout=30)
```

### 3. Clean Up

Always clean up after tests:
```python
try:
    scenario.execute()
finally:
    coordinator.cleanup()
```

### 4. Verify Assumptions

Test your assumptions about failure behavior:
```python
# Don't assume - verify!
coordinator.create_partition([["node1"], ["node2", "node3"]])
assertions.assert_minority_cannot_elect_leader()  # Verify assumption
```

## Examples

See [examples/](./examples/) for complete examples:
- Split-brain prevention testing
- Partition tolerance verification
- Healing and recovery scenarios
- CAP theorem demonstrations

## Dependencies

- Python 3.8+
- Optional: `pyyaml` for scenario configuration
- Optional: `pytest` for test integration

## Versioning

Current: **0.1.0**

Follows [Semantic Versioning](https://semver.org/)

## References

- [Jepsen: Distributed Systems Safety Research](https://jepsen.io/)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [The Network is Reliable (Paper)](https://queue.acm.org/detail.cfm?id=2655736)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=network-partition-tester
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration sections above for scenario and coordinator settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
