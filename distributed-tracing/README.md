# Distributed Tracing

Request tracing and observability for distributed systems.

## Overview

Distributed tracing tracks requests across service boundaries, enabling debugging, performance analysis, and understanding system behavior in microservices architectures.

**Version**: 0.1.0

## Features

- ✅ **Trace Context Propagation** — Cross-service correlation
- ✅ **Span Collection** — Timing and metadata
- ✅ **Sampling** — Reduce overhead
- ✅ **Trace Visualization** — Waterfall diagrams

## Quick Start

```python
from tracing import Tracer

tracer = Tracer(service_name="api-service")

# Start trace
with tracer.start_span("process_request") as span:
    span.set_tag("user_id", "123")
    
    # Nested span
    with tracer.start_span("database_query", parent=span) as db_span:
        db_span.set_tag("query", "SELECT * FROM users")
        result = database.query()
    
    return result
```

## Concepts

### Trace Context

```python
# Extract context from incoming request
context = tracer.extract(request.headers)

# Start span with parent context
span = tracer.start_span("operation", parent_context=context)

# Inject context into outgoing request
headers = {}
tracer.inject(span.context, headers)
requests.get(url, headers=headers)
```

### Sampling

```python
# Sample 10% of traces
tracer = Tracer(
    service_name="api-service",
    sampling_rate=0.1
)
```

## Use Cases

- Performance debugging
- Dependency analysis
- Latency investigation
- Error tracking

## Standalone Installation

```bash
pip install git+https://github.com/navinBRuas/_DistributedSystems#subdirectory=distributed-tracing
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
