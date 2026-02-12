# Vector Clocks (Advanced)

Advanced vector clock implementations including dotted version vectors and interval tree clocks.

## Overview

Beyond basic vector clocks, this module provides state-of-the-art causality tracking for distributed systems: dotted version vectors (DVV) for precision, and interval tree clocks (ITC) for dynamic systems.

**Version**: 0.1.0

## Features

- ✅ **Dotted Version Vectors** — Precise causality tracking
- ✅ **Interval Tree Clocks** — Dynamic participants
- ✅ **Causal History** — Complete causality graphs
- ✅ **Compact Representation** — Optimized storage

## Quick Start

```python
from dotted_version_vector import DVV

# Create DVV
dvv = DVV(actor="node1")

# Track events
dvv.event("write", value="data")

# Merge concurrent updates
dvv.merge(other_dvv)

# Check causality
if dvv.happens_before(other_dvv):
    print("Causal relationship")
```

## Use Cases

- CRDTs with precise causality
- Collaborative editing systems
- Distributed databases
- Event sourcing systems

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=vector-clocks-advanced
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
