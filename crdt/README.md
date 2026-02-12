# Conflict-Free Replicated Data Types (CRDTs)

Production implementations of CRDTs for building eventually consistent distributed systems without coordination.

## Overview

CRDTs are data structures that can be replicated across multiple nodes, updated independently, and merged automatically without conflicts. This project provides common CRDT implementations used in distributed databases, collaborative editing, and real-time sync systems.

**Version**: 0.1.0

## Features

- ✅ **G-Counter** — Grow-only counter (increment-only)
- ✅ **PN-Counter** — Positive-negative counter (increment/decrement)
- ✅ **LWW-Register** — Last-write-wins register
- ✅ **OR-Set** — Observed-remove set (add/remove elements)
- ✅ **G-Set** — Grow-only set
- ✅ **2P-Set** — Two-phase set (add once, remove once)
- ✅ **LWW-Map** — Last-write-wins map
- ✅ **Causal Context** — Vector clock tracking

## Architecture

```
crdt/
├── src/
│   ├── crdt_base.py           # Base CRDT interface
│   ├── g_counter.py           # Grow-only counter
│   ├── pn_counter.py          # Positive-negative counter
│   ├── lww_register.py        # Last-write-wins register
│   ├── or_set.py              # Observed-remove set
│   ├── g_set.py               # Grow-only set
│   ├── two_phase_set.py       # Two-phase set
│   ├── lww_map.py             # Last-write-wins map
│   └── causal_context.py      # Vector clock tracking
├── examples/
│   ├── distributed_counter.py # Counter synchronization
│   ├── collaborative_edit.py  # Real-time editing
│   └── shopping_cart.py       # Distributed cart
├── tests/
│   ├── test_convergence.py
│   ├── test_properties.py
│   └── test_merge.py
├── VERSION
└── requirements.txt
```

## Quick Start

### G-Counter (Grow-Only Counter)

```python
from g_counter import GCounter

# Node 1
counter1 = GCounter(node_id="node1")
counter1.increment()
counter1.increment()
print(counter1.value())  # 2

# Node 2
counter2 = GCounter(node_id="node2")
counter2.increment()
print(counter2.value())  # 1

# Merge counters
counter1.merge(counter2)
print(counter1.value())  # 3 (converged)
```

### PN-Counter (Increment/Decrement)

```python
from pn_counter import PNCounter

counter = PNCounter(node_id="node1")

counter.increment(5)   # +5
counter.decrement(2)   # -2
print(counter.value()) # 3

# Replicate to another node
counter2 = PNCounter(node_id="node2")
counter2.merge(counter)
print(counter2.value()) # 3
```

## CRDT Types

### 1. G-Counter (Grow-Only Counter)

Monotonically increasing counter:

```python
from g_counter import GCounter

# Create counter
counter = GCounter(node_id="replica1")

# Increment only
counter.increment(value=10)
print(counter.value())  # 10

# Get state for replication
state = counter.get_state()

# Merge with remote replica
counter.merge(other_counter)
```

**Properties**:
- ✓ Commutative: merge order doesn't matter
- ✓ Associative: grouping doesn't matter  
- ✓ Idempotent: merging twice has same effect as once
- ✓ Convergent: all replicas eventually converge

**Use cases**: Page views, likes, downloads

### 2. PN-Counter (Positive-Negative Counter)

Counter supporting increment and decrement:

```python
from pn_counter import PNCounter

counter = PNCounter(node_id="node1")

counter.increment(10)  # +10
counter.decrement(3)   # -3
print(counter.value()) # 7

# Handles concurrent updates
counter2 = PNCounter(node_id="node2")
counter2.increment(5)

# Merge
counter.merge(counter2)
print(counter.value()) # 12
```

**Implementation**: Two G-Counters (P and N)
- Value = P - N

**Use cases**: Inventory, ratings, vote counts

### 3. LWW-Register (Last-Write-Wins Register)

Single-value register resolved by timestamp:

```python
from lww_register import LWWRegister

register = LWWRegister(node_id="node1")

# Write values with timestamps
register.write("Alice", timestamp=100)
register.write("Bob", timestamp=200)

print(register.read())  # "Bob" (latest timestamp)

# Merge with concurrent writes
register2 = LWWRegister(node_id="node2")
register2.write("Charlie", timestamp=150)

register.merge(register2)
print(register.read())  # "Bob" (200 > 150)
```

**Conflict resolution**: Highest timestamp wins
- Ties broken by node ID

**Use cases**: User profiles, configuration values

### 4. OR-Set (Observed-Remove Set)

Set supporting add and remove:

```python
from or_set import ORSet

set1 = ORSet(node_id="node1")
set2 = ORSet(node_id="node2")

# Add elements
set1.add("apple")
set1.add("banana")

# Remove element
set1.remove("apple")

# Concurrent add
set2.add("apple")  # Different context

# Merge
set1.merge(set2)
print(set1.elements())  # {"apple", "banana"}
# Concurrent add wins over remove
```

**Properties**:
- Add-wins semantics
- Tracks causal context per element
- Handles concurrent add/remove

**Use cases**: Shopping carts, collaborative editing

### 5. G-Set (Grow-Only Set)

Set supporting only additions:

```python
from g_set import GSet

set1 = GSet()
set1.add("item1")
set1.add("item2")

set2 = GSet()
set2.add("item3")

# Merge (union)
set1.merge(set2)
print(set1.elements())  # {"item1", "item2", "item3"}
```

**Use cases**: Tags, labels, immutable collections

### 6. 2P-Set (Two-Phase Set)

Set supporting add and remove (once each):

```python
from two_phase_set import TwoPhaseSet

set = TwoPhaseSet()

set.add("item")
print("item" in set)  # True

set.remove("item")
print("item" in set)  # False

set.add("item")       # No effect - already removed
print("item" in set)  # False
```

**Constraint**: Once removed, cannot be re-added

**Use cases**: Soft deletes, tombstones

### 7. LWW-Map (Last-Write-Wins Map)

Key-value map with LWW semantics:

```python
from lww_map import LWWMap

map = LWWMap(node_id="node1")

# Put key-value pairs
map.put("name", "Alice", timestamp=100)
map.put("age", 30, timestamp=100)

# Update value
map.put("name", "Bob", timestamp=200)

print(map.get("name"))  # "Bob"

# Remove key
map.remove("age", timestamp=300)
print(map.get("age"))   # None
```

**Use cases**: Distributed caches, user sessions

## Convergence Properties

### Strong Eventual Consistency

All replicas that have received same updates converge to same state:

```python
# Node 1
counter1 = GCounter("node1")
counter1.increment(5)

# Node 2  
counter2 = GCounter("node2")
counter2.increment(10)

# Bidirectional sync
counter1.merge(counter2)
counter2.merge(counter1)

# Both converged to same value
assert counter1.value() == counter2.value() == 15
```

### Commutativity

Merge order doesn't affect result:

```python
# Scenario 1: A merges B, then C
a1 = GCounter("a")
a1.increment(1)
a1.merge(b)
a1.merge(c)

# Scenario 2: A merges C, then B  
a2 = GCounter("a")
a2.increment(1)
a2.merge(c)
a2.merge(b)

# Same result
assert a1.value() == a2.value()
```

### Idempotence

Merging same state multiple times is safe:

```python
counter = GCounter("node1")
counter.increment(5)

# Merge duplicate messages
counter.merge(other)
counter.merge(other)  # Duplicate - no effect

# Result unchanged
```

## Implementation Patterns

### State-Based CRDTs (CvRDT)

Replicate full state, merge on receive:

```python
class StateCRDT:
    def get_state(self):
        """Get current state for replication"""
        return self.state
    
    def merge(self, other_state):
        """Merge with remote state"""
        self.state = self.join(self.state, other_state)
```

### Operation-Based CRDTs (CmRDT)

Replicate operations, apply on receive:

```python
class OpCRDT:
    def increment(self, value):
        """Local operation"""
        op = ("increment", value, self.node_id, timestamp())
        self.apply(op)
        self.broadcast(op)
    
    def apply(self, operation):
        """Apply operation to state"""
        # Must be commutative
        pass
```

## Use Cases

### 1. Distributed Counter

```python
class PageViewCounter:
    def __init__(self, page_id):
        self.page_id = page_id
        self.counter = GCounter(node_id=get_node_id())
    
    def record_view(self):
        self.counter.increment()
    
    def get_views(self):
        return self.counter.value()
    
    def sync_with(self, other_node):
        self.counter.merge(other_node.counter)
```

### 2. Shopping Cart

```python
class ShoppingCart:
    def __init__(self, user_id, node_id):
        self.user_id = user_id
        self.items = ORSet(node_id=node_id)
    
    def add_item(self, item_id):
        self.items.add(item_id)
    
    def remove_item(self, item_id):
        self.items.remove(item_id)
    
    def get_items(self):
        return self.items.elements()
    
    def merge(self, other_cart):
        self.items.merge(other_cart.items)
```

### 3. User Profile

```python
class UserProfile:
    def __init__(self, user_id, node_id):
        self.user_id = user_id
        self.fields = LWWMap(node_id=node_id)
    
    def update_field(self, key, value):
        timestamp = time.time()
        self.fields.put(key, value, timestamp)
    
    def get_field(self, key):
        return self.fields.get(key)
    
    def merge(self, other_profile):
        self.fields.merge(other_profile.fields)
```

## Performance

### Memory Overhead

| CRDT Type | Overhead per Node | Total |
|-----------|-------------------|-------|
| G-Counter | O(N) | O(N) per counter |
| PN-Counter | O(N) | O(2N) per counter |
| OR-Set | O(N × M) | N=nodes, M=elements |
| LWW-Register | O(1) | O(1) |

### Merge Complexity

| CRDT Type | Time Complexity | Space |
|-----------|----------------|-------|
| G-Counter | O(N) | O(N) |
| PN-Counter | O(N) | O(N) |
| OR-Set | O(M) | O(M) |
| LWW-Register | O(1) | O(1) |

## Comparison

### CRDTs vs Consensus

| Aspect | CRDTs | Consensus |
|--------|-------|-----------|
| Coordination | None | Required |
| Latency | Low (local) | High (network RTT) |
| Availability | High | Lower |
| Consistency | Eventual | Strong |
| Conflicts | Automatic | Manual |

### State-Based vs Op-Based

| Aspect | State-Based | Op-Based |
|--------|-------------|----------|
| Network | Send full state | Send operations |
| Bandwidth | Higher | Lower |
| Complexity | Simpler | More complex |
| Delivery | Idempotent | Exactly-once |

## Testing

```bash
# Run tests
python -m pytest tests/

# Convergence tests
python tests/test_convergence.py --nodes 10 --operations 1000

# Property tests
python tests/test_properties.py
```

## Monitoring

```python
# Get CRDT statistics
stats = counter.get_stats()

print(f"Local operations: {stats['local_ops']}")
print(f"Merges: {stats['merges']}")
print(f"State size: {stats['state_size_bytes']} bytes")
print(f"Node count: {stats['node_count']}")
```

## Dependencies

- Python 3.8+
- No external dependencies (stdlib only)

## Versioning

Current: **0.1.0**

## References

- [A Comprehensive Study of CRDTs](https://hal.inria.fr/inria-00555588/document)
- [Conflict-free Replicated Data Types (Shapiro et al.)](https://arxiv.org/abs/1805.06358)
- [CRDT Tech](https://crdt.tech/)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=crdt
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
