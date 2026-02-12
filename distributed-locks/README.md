# Distributed Locks

Production-grade distributed locking mechanisms for coordinating access to shared resources across distributed systems.

## Overview

This project provides multiple distributed lock implementations including Redlock, lease-based locks, and fencing tokens to prevent split-brain scenarios and ensure mutual exclusion in distributed environments.

**Version**: 0.1.0

## Features

- ✅ **Redlock Algorithm** — Redis-based distributed locks (Antirez)
- ✅ **Lease-Based Locks** — Time-bounded locks with automatic expiration
- ✅ **Fencing Tokens** — Monotonic tokens to prevent stale lock holders
- ✅ **Try-Lock Pattern** — Non-blocking lock acquisition
- ✅ **Lock Renewal** — Extend lock duration for long operations
- ✅ **Deadlock Detection** — Identify and resolve deadlocks

## Architecture

```
distributed-locks/
├── src/
│   ├── distributed_lock.py    # Main lock interface
│   ├── redlock.py              # Redlock implementation
│   ├── lease_lock.py           # Lease-based locks
│   ├── fencing_tokens.py       # Fencing token manager
│   └── deadlock_detector.py   # Deadlock detection
├── examples/
│   ├── critical_section.py    # Basic mutual exclusion
│   ├── leader_protected.py    # Leader-based coordination
│   └── transaction_lock.py    # Distributed transactions
├── tests/
│   ├── test_redlock.py
│   ├── test_safety.py
│   └── test_performance.py
├── VERSION
└── requirements.txt
```

## Quick Start

### Basic Lock Usage

```python
from distributed_lock import DistributedLock

# Create a distributed lock
lock = DistributedLock(
    resource_name="inventory:item:12345",
    servers=["redis://localhost:6379"],
    ttl=10  # Lock expires after 10 seconds
)

# Acquire lock
if lock.acquire():
    try:
        # Critical section - only one holder at a time
        update_inventory()
    finally:
        lock.release()
else:
    print("Failed to acquire lock")
```

### Context Manager Pattern

```python
with DistributedLock("order:processing", servers=redis_servers) as lock:
    if lock.acquired:
        process_order()
```

## Algorithms

### 1. Redlock Algorithm

Redis-based distributed lock with quorum:

```python
from redlock import Redlock

# Require majority of Redis instances
lock = Redlock(
    resource="payment:transaction:xyz",
    servers=[
        "redis://host1:6379",
        "redis://host2:6379",
        "redis://host3:6379",
        "redis://host4:6379",
        "redis://host5:6379"
    ],
    ttl=10000  # milliseconds
)

# Acquire with quorum (3/5 servers)
if lock.acquire():
    # Safe to proceed
    process_payment()
    lock.release()
```

**Properties**:
- Requires majority quorum (N/2 + 1)
- Tolerates minority failures
- Time-based expiration for safety
- Fencing tokens for ordering

### 2. Lease-Based Locks

Time-bounded locks with automatic expiration:

```python
from lease_lock import LeaseLock

lock = LeaseLock(
    resource="cron:daily_job",
    duration=300,  # 5 minutes
    coordinator="zookeeper://localhost:2181"
)

if lock.acquire():
    # Lock automatically expires after 5 minutes
    run_daily_job()
    lock.release()
```

**Features**:
- Automatic expiration prevents stuck locks
- Renewable leases for long operations
- No need for explicit release on crash

### 3. Fencing Tokens

Prevent operations from stale lock holders:

```python
from fencing_tokens import FencedLock

lock = FencedLock(resource="database:schema_migration")

# Acquire lock and get fencing token
token = lock.acquire_with_token()

if token:
    # Perform operation with token
    database.execute(migration, fencing_token=token)
    lock.release()
```

**How it works**:
- Each lock acquisition gets monotonically increasing token
- Operations require valid token
- Stale tokens rejected by resource

## Use Cases

### 1. Critical Section Protection

```python
class BankAccount:
    def __init__(self, account_id):
        self.account_id = account_id
        self.lock = DistributedLock(f"account:{account_id}")
    
    def transfer(self, amount, to_account):
        with self.lock:
            # Only one transfer at a time
            balance = self.get_balance()
            if balance >= amount:
                self.deduct(amount)
                to_account.add(amount)
```

### 2. Singleton Resource Access

```python
class DatabaseMigration:
    def run(self):
        lock = DistributedLock("db:migration", ttl=3600)
        
        if not lock.acquire():
            print("Migration already running")
            return
        
        try:
            # Only one migration runs across cluster
            self.apply_migrations()
        finally:
            lock.release()
```

### 3. Rate Limiting

```python
class DistributedRateLimiter:
    def allow_request(self, user_id):
        lock = DistributedLock(
            f"rate_limit:{user_id}",
            ttl=1000  # 1 second window
        )
        
        if lock.acquire(blocking=False):
            # Request allowed
            return True
        else:
            # Rate limited
            return False
```

## Lock Patterns

### Try-Lock (Non-blocking)

```python
lock = DistributedLock("resource")

if lock.try_acquire(timeout=0):
    # Lock acquired immediately
    do_work()
    lock.release()
else:
    # Lock not available, do something else
    schedule_retry()
```

### Blocking Acquire with Timeout

```python
# Wait up to 5 seconds for lock
if lock.acquire(timeout=5):
    # Got lock within timeout
    do_work()
    lock.release()
else:
    # Timeout - lock not available
    handle_timeout()
```

### Lock Renewal

```python
lock = DistributedLock("long_operation", ttl=10)

if lock.acquire():
    try:
        for chunk in large_dataset:
            process(chunk)
            
            # Renew lock every few seconds
            lock.renew()
    finally:
        lock.release()
```

## Safety Guarantees

### 1. Mutual Exclusion

Only one lock holder at any time:

```python
# Test mutual exclusion
def test_mutual_exclusion():
    lock1 = DistributedLock("resource")
    lock2 = DistributedLock("resource")
    
    assert lock1.acquire()
    assert not lock2.acquire()  # Cannot acquire
    
    lock1.release()
    assert lock2.acquire()  # Now can acquire
```

### 2. Deadlock Freedom

Locks automatically expire to prevent deadlocks:

```python
lock = DistributedLock("resource", ttl=10)
lock.acquire()

# If process crashes, lock expires after 10 seconds
# Other processes can then acquire it
```

### 3. Fencing Tokens

Prevent stale operations:

```python
# Client 1 acquires lock (token=1)
token1 = lock.acquire_with_token()
# Network delay...

# Client 2 acquires lock (token=2) 
token2 = lock.acquire_with_token()
# Completes operation quickly

# Client 1 finally tries operation
database.write(data, token=token1)  # REJECTED - stale token
```

## Configuration

```python
from distributed_lock import LockConfig

config = LockConfig(
    ttl=10000,              # Lock TTL (ms)
    retry_delay=200,        # Retry delay (ms)
    retry_count=3,          # Max retries
    clock_drift_factor=0.01,# Clock drift compensation
    quorum_size=3           # Redlock quorum
)

lock = DistributedLock("resource", config=config)
```

## Performance

### Benchmarks

| Operation | Latency (p50) | Latency (p99) |
|-----------|---------------|---------------|
| Acquire   | 1-2 ms        | 5-10 ms       |
| Release   | 0.5-1 ms      | 2-5 ms        |
| Renew     | 0.5-1 ms      | 2-5 ms        |

### Throughput

- Single lock: ~500-1000 ops/sec
- Independent locks: ~10,000+ ops/sec

### Optimization Tips

1. **Reduce TTL**: Shorter TTL = faster recovery from failures
2. **Local Caching**: Cache lock state for short-lived locks
3. **Batching**: Group multiple resources under one lock
4. **Try-Lock**: Use non-blocking when possible

## Monitoring

```python
# Get lock metrics
metrics = lock.get_metrics()

print(f"Acquisitions: {metrics['acquire_count']}")
print(f"Releases: {metrics['release_count']}")
print(f"Renewals: {metrics['renew_count']}")
print(f"Failures: {metrics['failure_count']}")
print(f"Avg hold time: {metrics['avg_hold_time_ms']}ms")
```

## Deadlock Detection

```python
from deadlock_detector import DeadlockDetector

detector = DeadlockDetector()

# Register lock acquisition
detector.acquire_lock(process_id="p1", resource="r1")
detector.acquire_lock(process_id="p2", resource="r2")

# Wait for resources
detector.wait_for(process_id="p1", resource="r2")
detector.wait_for(process_id="p2", resource="r1")

# Detect deadlock
if detector.detect_deadlock():
    print("Deadlock detected!")
    cycle = detector.get_deadlock_cycle()
    print(f"Cycle: {cycle}")
```

## Comparison

### vs Leader Election

- **Locks**: Short-lived, for critical sections
- **Leader Election**: Long-lived, for coordination

### vs Semaphores

- **Locks**: Binary (0 or 1)
- **Semaphores**: Counting (0 to N)

### vs Transactions

- **Locks**: Explicit acquire/release
- **Transactions**: ACID guarantees, isolation levels

## Testing

```bash
# Run tests
python -m pytest tests/

# Safety tests
python tests/test_safety.py --processes 10

# Performance benchmarks
python tests/test_performance.py --duration 60
```

## Integration Examples

### With Redis

```python
import redis

class RedisDistributedLock:
    def __init__(self, redis_client, resource, ttl=10):
        self.redis = redis_client
        self.resource = resource
        self.ttl = ttl
        self.token = None
    
    def acquire(self):
        import uuid
        self.token = str(uuid.uuid4())
        
        # SET NX EX: set if not exists with expiration
        return self.redis.set(
            self.resource,
            self.token,
            nx=True,
            ex=self.ttl
        )
    
    def release(self):
        # Use Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis.eval(script, 1, self.resource, self.token)
```

### With etcd

```python
import etcd3

class EtcdDistributedLock:
    def __init__(self, etcd_client, resource, ttl=10):
        self.etcd = etcd_client
        self.resource = resource
        self.ttl = ttl
        self.lease = None
    
    def acquire(self):
        # Create lease
        self.lease = self.etcd.lease(self.ttl)
        
        # Try to create key with lease
        success = self.etcd.put_if_not_exists(
            self.resource,
            "locked",
            lease=self.lease
        )
        return success
```

## Dependencies

- Python 3.8+
- Optional: `redis` for Redis backend
- Optional: `kazoo` for ZooKeeper backend
- Optional: `etcd3` for etcd backend

## Versioning

Current: **0.1.0**

## References

- [Redlock Algorithm](https://redis.io/topics/distlock)
- [How to do distributed locking (Martin Kleppmann)](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
- [Leases: An Efficient Fault-Tolerant Mechanism](https://web.stanford.edu/class/cs240/readings/89-leases.pdf)

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=distributed-locks
```

## Usage
See the sections above and `examples/` for usage patterns.

## Configuration
See the Configuration section above for `LockConfig` settings.

## Version
`0.1.0` (see `VERSION.md`)

## Changelog
See `CHANGELOG.md`.

## License
MIT License. See repo root `LICENSE`.
