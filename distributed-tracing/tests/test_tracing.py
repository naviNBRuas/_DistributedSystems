import unittest
import time
import json
from tracing import Tracer, print_trace
from tracing.span import SpanContext

class TestTracing(unittest.TestCase):
    def setUp(self):
        self.tracer = Tracer(service_name="test-service")

    def test_basic_span(self):
        with self.tracer.start_span("test_op") as span:
            span.set_tag("key", "value")
            time.sleep(0.01)
        
        spans = self.tracer.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].operation_name, "test_op")
        self.assertEqual(spans[0].tags["key"], "value")
        self.assertGreater(spans[0].duration(), 0)

    def test_nested_spans(self):
        with self.tracer.start_span("root") as parent:
            with self.tracer.start_span("child", parent=parent) as child:
                pass
        
        spans = self.tracer.get_finished_spans()
        self.assertEqual(len(spans), 2)
        
        child = next(s for s in spans if s.operation_name == "child")
        root = next(s for s in spans if s.operation_name == "root")
        
        self.assertEqual(child.context.trace_id, root.context.trace_id)
        self.assertEqual(child.context.parent_id, root.context.span_id)

    def test_context_injection_extraction(self):
        with self.tracer.start_span("client_op") as span:
            headers = {}
            self.tracer.inject(span.context, headers)
            
            self.assertIn("x-trace-id", headers)
            self.assertIn("x-span-id", headers)
            self.assertIn("x-trace-sampled", headers)

            extracted_context = self.tracer.extract(headers)
            self.assertEqual(extracted_context.trace_id, span.context.trace_id)
            self.assertEqual(extracted_context.span_id, span.context.span_id)
            self.assertEqual(extracted_context.sampled, span.context.sampled)

    def test_sampling(self):
        # Test forced sampling (rate=1.0)
        tracer_always = Tracer("always", sampling_rate=1.0)
        with tracer_always.start_span("op") as span:
            pass
        self.assertTrue(span.context.sampled)
        self.assertEqual(len(tracer_always.get_finished_spans()), 1)

        # Test no sampling (rate=0.0)
        tracer_never = Tracer("never", sampling_rate=0.0)
        with tracer_never.start_span("op") as span:
            pass
        self.assertFalse(span.context.sampled)
        self.assertEqual(len(tracer_never.get_finished_spans()), 0)

    def test_visualization_smoke(self):
        # Just ensure it doesn't crash
        with self.tracer.start_span("root") as root:
             with self.tracer.start_span("child", parent=root):
                 time.sleep(0.01)
        
        print_trace(self.tracer.get_finished_spans())

if __name__ == '__main__':
    unittest.main()
