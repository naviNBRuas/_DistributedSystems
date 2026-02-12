# Byzantine Consensus

Byzantine fault-tolerant consensus protocols for adversarial environments.

## Overview

Byzantine consensus enables agreement among nodes when some may be faulty or malicious. Implements PBFT (Practical Byzantine Fault Tolerance) for building resilient distributed systems.

**Version**: 0.1.0

## Features

- ✅ **PBFT Protocol** — Practical Byzantine Fault Tolerance
- ✅ **View Changes** — Leader replacement logic implemented
- ✅ **Logging** — Comprehensive debug and info logging
- ✅ **3f+1 Nodes** — Tolerate f Byzantine failures

## Quick Start

```python
from pbft import PBFTNode, InMemoryNetwork

# Create Network
network = InMemoryNetwork()

# Create PBFT cluster (4 nodes, tolerate 1 Byzantine)
nodes = [
    PBFTNode(node_id=i, total_nodes=4, network=network) for i in range(4)
]

# Client request
request = nodes[0].propose("execute_transaction")

# Consensus reached when 2f+1 nodes agree
if request.committed:
    print("Transaction committed")
```

## Byzantine Faults

- Crash failures
- Message tampering
- Arbitrary behavior
- Colluding nodes

## Properties

- **Safety**: All honest nodes agree
- **Liveness**: Progress under async
- **Fault tolerance**: Up to f < n/3 Byzantine nodes

## Performance

| Nodes | Faults Tolerated | Message Complexity |
|-------|------------------|--------------------|
| 4 | 1 | O(n²) |
| 7 | 2 | O(n²) |
| 10 | 3 | O(n²) |

## Use Cases

- Blockchain systems
- Financial systems
- Critical infrastructure
- Adversarial networks

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=byzantine-consensus
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