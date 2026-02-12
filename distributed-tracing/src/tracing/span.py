import time
import json
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .tracer import Tracer

class SpanContext:
    def __init__(self, trace_id: str, span_id: str, parent_id: Optional[str] = None, sampled: bool = True):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_id = parent_id
        self.sampled = sampled

    def __repr__(self) -> str:
        return f"SpanContext(trace_id={self.trace_id}, span_id={self.span_id}, parent_id={self.parent_id}, sampled={self.sampled})"

class Span:
    def __init__(self, tracer: 'Tracer', operation_name: str, context: SpanContext):
        self.tracer = tracer
        self.operation_name = operation_name
        self.context = context
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.logs: list = []

    def set_tag(self, key: str, value: Any) -> 'Span':
        self.tags[key] = value
        return self

    def log(self, **kwargs: Any) -> 'Span':
        self.logs.append({"timestamp": time.time(), "fields": kwargs})
        return self

    def finish(self) -> None:
        if self.end_time is not None:
            return
        self.end_time = time.time()
        self.tracer.record(self)

    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return 0

    def __enter__(self) -> 'Span':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            self.set_tag("error", True)
            self.set_tag("error.message", str(exc_val))
        self.finish()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_name": self.operation_name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_id": self.context.parent_id,
            "sampled": self.context.sampled,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration(),
            "tags": self.tags,
            "logs": self.logs
        }
