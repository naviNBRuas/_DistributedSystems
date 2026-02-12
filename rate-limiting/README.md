# Rate Limiting

Distributed rate limiting algorithms for API throttling and traffic control.

## Overview

Rate limiting protects services from overload by controlling request rates. This project implements token bucket, leaky bucket, sliding window, and distributed rate limiting algorithms.

**Version**: 0.1.0

## Features

- ✅ **Token Bucket** — Burst support with refill
- ✅ **Leaky Bucket** — Smooth rate limiting
- ✅ **Sliding Window** — Time-based windows
- ✅ **Distributed Limiter** — Redis-based coordination

## Quick Start

```python
from rate_limiter import TokenBucketLimiter

# 100 requests per second, burst of 10
limiter = TokenBucketLimiter(
    rate=100,
    capacity=10
)

# Check if request allowed
if limiter.allow_request():
    process_request()
else:
    return_429_error()
```

## Algorithms

### 1. Token Bucket

```python
limiter = TokenBucketLimiter(rate=10, capacity=20)

for i in range(25):
    if limiter.allow_request():
        print(f"Request {i}: Allowed")
    else:
        print(f"Request {i}: Rate limited")
```

### 2. Sliding Window

```python
limiter = SlidingWindowLimiter(
    window_size=60,  # 60 seconds
    max_requests=100
)
```

### 3. Distributed Rate Limiting

```python
from distributed_limiter import RedisRateLimiter

limiter = RedisRateLimiter(
    redis_client=redis_client,
    key="api:user:123",
    max_requests=1000,
    window=60
)

if limiter.allow_request():
    # Process request
    pass
```

## Use Cases

- API throttling
- DDoS protection
- Fair resource allocation
- Cost control

## Performance

| Algorithm | Memory | Accuracy | Distributed |
|-----------|--------|----------|-------------|
| Token Bucket | O(1) | Exact | Challenging |
| Leaky Bucket | O(1) | Exact | Challenging |
| Sliding Window | O(W) | Exact | Yes (Redis) |

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=rate-limiting
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
