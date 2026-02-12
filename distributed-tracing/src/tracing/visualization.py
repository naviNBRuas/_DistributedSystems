
from typing import List, Dict

from .span import Span



def print_trace(spans: List[Span]) -> None:

    if not spans:

        print("No spans to display.")

        return



    traces: Dict[str, List[Span]] = {}

    for span in spans:

        tid = span.context.trace_id

        if tid not in traces:

            traces[tid] = []

        traces[tid].append(span)



    for tid, trace_spans in traces.items():

        print(f"\nTrace: {tid}")

        trace_spans.sort(key=lambda s: s.start_time)

        

        if not trace_spans:

            continue



        start_time = trace_spans[0].start_time

        end_time = max((s.end_time or s.start_time) for s in trace_spans)

        total_duration = end_time - start_time

        

        if total_duration <= 0:

            total_duration = 0.000001 # Avoid div by zero



        max_width = 50 



        for span in trace_spans:

            offset = span.start_time - start_time

            duration = span.duration()

            

            offset_percent = offset / total_duration

            duration_percent = duration / total_duration

            

            indent = int(offset_percent * max_width)

            width = max(1, int(duration_percent * max_width))

            

            bar = " " * indent + "█" * width

            

            name = span.operation_name[:25].ljust(27)

            dur_str = f"{duration*1000:.2f}ms"

            

            print(f"{name} | {bar} {dur_str}")

        print("-" * 80)


