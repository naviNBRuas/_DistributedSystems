# Distributed Transactions

Two-phase commit, three-phase commit, and Saga pattern implementations for distributed transaction coordination.

## Overview

Distributed transactions enable atomic operations across multiple services while managing failures and maintaining consistency. This project provides practical implementations of 2PC, 3PC, and Saga patterns.

**Version**: 0.1.0

## Features

- ✅ **Two-Phase Commit (2PC)** — Atomic commit protocol
- ✅ **Three-Phase Commit (3PC)** — Non-blocking variant
- ✅ **Saga Pattern** — Long-running transactions
- ✅ **Compensating Actions** — Rollback logic
- ✅ **Timeout Handling** — Prevent indefinite blocking

## Quick Start

```python
from two_phase_commit import TwoPhaseCoordinator, TwoPhaseParticipant

# Create coordinator
coordinator = TwoPhaseCoordinator(timeout=5.0)

# Register participants (services)
# In a real app, these would wrap RPC clients
service_a = TwoPhaseParticipant("service_a")
service_b = TwoPhaseParticipant("service_b")

coordinator.register_participant(service_a)
coordinator.register_participant(service_b)

# Execute distributed transaction
success = coordinator.execute_transaction(
    operations=[
        ("service_a", "debit", {"account": "A", "amount": 100}),
        ("service_b", "credit", {"account": "B", "amount": 100})
    ]
)

if success:
    print("Transaction committed")
else:
    print("Transaction aborted")
```

## Algorithms

### 1. Two-Phase Commit (2PC)

**Phase 1 - Prepare**:
- Coordinator sends PREPARE to all participants
- Participants vote YES/NO
- Participants write undo/redo logs

**Phase 2 - Commit/Abort**:
- If all YES: Coordinator sends COMMIT
- If any NO: Coordinator sends ABORT

```python
coordinator = TwoPhaseCoordinator()
coordinator.register_participant(p1)
result = coordinator.execute_transaction(operations)
```

### 2. Saga Pattern

Long-running transactions with compensations:

```python
from saga import SagaOrchestrator

saga = SagaOrchestrator()

# Define steps with compensations
saga.add_step(
    action=lambda: order_service.create_order(),
    compensation=lambda: order_service.cancel_order()
)

saga.add_step(
    action=lambda: payment_service.charge(),
    compensation=lambda: payment_service.refund()
)

# Execute
saga.execute()
```

## Use Cases

- Distributed database transactions
- Microservice coordination
- Financial transfers
- Order processing pipelines

## References

- [Gray & Lamport: Consensus on Transaction Commit](https://lamport.azurewebsites.net/pubs/trans.pdf)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=distributed-transactions
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
