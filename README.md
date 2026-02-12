# _DistributedSystems

Foundational distributed systems algorithms and runtime components, packaged for independent reuse.

## Overview

`_DistributedSystems` contains modular implementations of consensus, replication, data structures, coordination, and control primitives for resilient distributed platforms.

## Packages

- [`bloom-filters`](./bloom-filters/)
- [`byzantine-consensus`](./byzantine-consensus/)
- [`clock-skew-simulator`](./clock-skew-simulator/)
- [`consistent-hashing`](./consistent-hashing/)
- [`crdt`](./crdt/)
- [`distributed-locks`](./distributed-locks/)
- [`distributed-tracing`](./distributed-tracing/)
- [`distributed-transactions`](./distributed-transactions/)
- [`eventual-consistency-patterns`](./eventual-consistency-patterns/)
- [`gossip-protocol`](./gossip-protocol/)
- [`leader-election`](./leader-election/)
- [`merkle-trees`](./merkle-trees/)
- [`network-partition-tester`](./network-partition-tester/)
- [`quorum-systems`](./quorum-systems/)
- [`raft-from-scratch`](./raft-from-scratch/)
- [`rate-limiting`](./rate-limiting/)
- [`service-discovery`](./service-discovery/)
- [`vector-clocks-advanced`](./vector-clocks-advanced/)

## Installation

### Option A: consume the whole repository

```bash
git submodule add https://github.com/navinBRuas/_DistributedSystems.git vendor/distributed-systems
```

### Option B: install a single package

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=raft-from-scratch
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=consistent-hashing
```

## Usage

1. Choose a package that matches your use case.
2. Follow that package's `README.md` for APIs and examples.
3. Compose packages via documented interfaces only.

## Development

- Keep implementations deterministic and well-tested.
- Run tests from the selected package before publishing changes.
- Maintain package-level docs and changelogs.

## Governance & docs

- [GOVERNANCE.md](./GOVERNANCE.md)
- [SECURITY.md](./SECURITY.md)
- [SUPPORT.md](./SUPPORT.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)

## Version

`0.1.0`

## License

See [LICENSE](./LICENSE).
