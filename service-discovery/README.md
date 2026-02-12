# Service Discovery

Dynamic service registration, discovery, and health checking for microservices architectures.

## Overview

Service discovery enables services to find and communicate with each other without hardcoded addresses. This module provides a robust, thread-safe registry with automatic health checking, load balancing, and event notifications.

**Version**: 0.1.0

## Features

- ✅ **Service Registry** — Thread-safe central service catalog
- ✅ **Concurrent Health Checking** — Parallel probes for scalability and performance
- ✅ **Observer Pattern** — Event notifications for status changes (UP/DOWN)
- ✅ **Load Balancing** — Client-side round-robin service selection
- ✅ **Robust API** — Immutable discovery results and strict validation

## Quick Start

```python
from src.service_registry import ServiceRegistry, LoadBalancer

# Initialize registry with custom check interval and workers
registry = ServiceRegistry(health_check_interval=5.0, max_workers=10)

# Register service
registry.register(
    service_name="user-service",
    host="192.168.1.10",
    port=8080,
    metadata={"version": "0.1.0"},
    health_check_url="/health"
)

# Discover healthy services
instances = registry.discover("user-service")
if instances:
    instance = instances[0]
    print(f"Service found at {instance.get_address()}")
```

## Advanced Features

### Event Observers

Subscribe to service status changes to trigger alerts or logging.

```python
def on_status_change(instance, status):
    print(f"Alert: {instance.service_name} is now {status.value}")

registry.add_observer(on_status_change)
```

### Client-Side Load Balancing

Distribute traffic across available instances using Round-Robin.

```python
lb = LoadBalancer(registry)
instance = lb.get_instance("user-service")

if instance:
    # Connect to service
    url = f"http://{instance.get_address()}/api/resource"
    # ... perform request
```

## Architecture

- **ServiceRegistry**: Manages the lifecycle of service instances. It runs a background thread pool to perform concurrent health checks (HTTP probes and heartbeat validation).
- **ServiceInstance**: Represents a single service node. It is immutable when returned by discovery methods.
- **Thread Safety**: All registry operations are protected by locks, ensuring safe concurrent access.

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=service-discovery
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