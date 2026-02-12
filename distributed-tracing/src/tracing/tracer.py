import uuid
import random
from typing import Optional, Dict, List
from .span import Span, SpanContext

class Tracer:
    def __init__(self, service_name: str, sampling_rate: float = 1.0):
        self.service_name = service_name
        self.sampling_rate = sampling_rate
        self.spans: List[Span] = []

    def start_span(self, operation_name: str, parent: Optional[Span] = None, parent_context: Optional[SpanContext] = None) -> Span:
        trace_id = None
        parent_id = None
        sampled = True

        if parent:
            trace_id = parent.context.trace_id
            parent_id = parent.context.span_id
            sampled = parent.context.sampled
        elif parent_context:
            trace_id = parent_context.trace_id
            parent_id = parent_context.span_id
            sampled = parent_context.sampled
        
        # New trace
        if not trace_id:
            trace_id = str(uuid.uuid4())
            # Sampling decision for root span
            if self.sampling_rate < 1.0 and random.random() > self.sampling_rate:
                sampled = False
            else:
                sampled = True

        span_id = str(uuid.uuid4())
        context = SpanContext(trace_id, span_id, parent_id, sampled=sampled)
        span = Span(self, operation_name, context)
        return span

    def record(self, span: Span) -> None:
        if span.context.sampled:
            self.spans.append(span)

    def extract(self, carrier: Dict[str, str]) -> Optional[SpanContext]:
        trace_id = carrier.get('x-trace-id')
        span_id = carrier.get('x-span-id')
        sampled_str = carrier.get('x-trace-sampled')
        
        sampled = True
        if sampled_str == '0' or sampled_str == 'false':
            sampled = False
            
        if trace_id and span_id:
            return SpanContext(trace_id, span_id, sampled=sampled)
        return None

    def inject(self, context: SpanContext, carrier: Dict[str, str]) -> None:
        carrier['x-trace-id'] = context.trace_id
        carrier['x-span-id'] = context.span_id
        carrier['x-trace-sampled'] = '1' if context.sampled else '0'

    def get_finished_spans(self) -> List[Span]:
        return self.spans

    def clear(self) -> None:
        self.spans = []