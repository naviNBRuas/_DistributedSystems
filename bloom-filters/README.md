# Bloom Filters

Space-efficient probabilistic data structures for membership testing in distributed systems.

## Overview

Bloom filters enable fast, memory-efficient set membership tests with configurable false positive rates. Perfect for caching, deduplication, and reducing expensive lookups.

**Version**: 0.1.0

## Features

- ✅ **Standard Bloom Filter** — Constant-time membership tests
- ✅ **Counting Bloom Filter** — Support for deletions
- ✅ **Scalable Bloom Filter** — Dynamic growth
- ✅ **Optimal Parameters** — Auto-calculate k and m

## Quick Start

```python
from bloom_filter import BloomFilter

# Create filter: 1M elements, 1% false positive rate
bf = BloomFilter(expected_elements=1000000, false_positive_rate=0.01)

# Add elements
bf.add("user123")
bf.add("user456")

# Test membership
print("user123" in bf)  # True
print("user999" in bf)  # False (probably)
```

## Properties

- **No false negatives**: If element not in filter, definitely not in set
- **False positives possible**: If element in filter, might not be in set
- **Space efficient**: Much smaller than storing full set
- **Time efficient**: O(k) add/query where k is small constant

## Use Cases

- Cache filtering
- Duplicate detection
- Database query optimization
- Network packet filtering

## Implementation Details

- **Pure Python**: Zero external dependencies.
- **Efficient Storage**:
  - `BloomFilter` uses Python's arbitrary-precision integers as bitfields.
  - `CountingBloomFilter` uses `array` module for memory-efficient counters.
- **Fast Hashing**: Uses Double Hashing technique to generate $k$ hashes from 2 MD5 computations.
- **Robustness**: `ScalableBloomFilter` uses geometric series for error tightening to strictly bound the global false positive rate.

## Performance

| Operation | Time | Space |
|-----------|------|-------|
| Add | O(k) | O(m) bits |
| Query | O(k) | - |
| Memory | - | ~10 bits per element |

## References

- [Bloom, Burton H. (1970). Space/Time Trade-offs in Hash Coding](http://crystal.uta.edu/~mcguigan/cse6350/papers/Bloom.pdf)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=bloom-filters
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
