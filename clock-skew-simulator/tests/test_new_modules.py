import unittest
import time
import os
from src.ntp_simulator import NTPSimulator
from src.causality import CausalityAnalyzer
from src.visualizer import EventGraphVisualizer, ClockDriftVisualizer
from src.lamport_clock import LamportClock
from src.vector_clock import VectorClock

class TestNTPSimulator(unittest.TestCase):
    def test_sync(self):
        nodes = ["n1", "n2", "n3"]
        sim = NTPSimulator(nodes, max_clock_skew=1.0)
        
        # Initial skew check
        initial_skew = sim.get_max_skew()
        
        # Sync
        sim.synchronize()
        
        # Skew should be reduced (ideally close to 0 + network error)
        # Since network latency is small (0.01), skew should be small
        final_skew = sim.get_max_skew()
        
        # Note: In a simulation with drift, skew might not be 0 perfectly,
        # but it should be significantly better than 1.0 (if initial random was bad enough)
        # However, due to randomness, initial skew might be small.
        # But logically, synchronize should set clocks close to server time.
        
        # Verify client clocks are close to server clock
        server_clock = sim.get_clock("n1")
        server_time = server_clock.read()
        
        c2 = sim.get_clock("n2")
        c3 = sim.get_clock("n3")
        
        self.assertAlmostEqual(c2.read(), server_time, delta=0.05)
        self.assertAlmostEqual(c3.read(), server_time, delta=0.05)

class TestCausalityAnalyzer(unittest.TestCase):
    def test_lamport_causality(self):
        analyzer = CausalityAnalyzer()
        
        # A -> B
        analyzer.add_event("e1", "local", 1)
        analyzer.add_event("e2", "local", 2)
        
        self.assertTrue(analyzer.happens_before("e1", "e2"))
        self.assertFalse(analyzer.happens_before("e2", "e1"))
        
    def test_vector_causality(self):
        analyzer = CausalityAnalyzer()
        
        # A=[1,0], B=[1,1] -> A -> B
        analyzer.add_event("e1", "local", {"A":1, "B":0})
        analyzer.add_event("e2", "local", {"A":1, "B":1})
        
        self.assertTrue(analyzer.happens_before("e1", "e2"))
        
        # Concurrent: C=[0,1] vs A=[1,0]
        analyzer.add_event("e3", "local", {"A":0, "B":1})
        self.assertTrue(analyzer.concurrent("e1", "e3"))

class TestVisualizer(unittest.TestCase):
    def test_visualizer_no_crash(self):
        # Even without matplotlib, it should run without error (printing warning)
        viz = EventGraphVisualizer()
        viz.add_event("A", 1, "local")
        viz.add_event("B", 2, "local")
        viz.add_happens_before("A", "B")
        
        # Should not raise exception
        viz.render("test_graph.png")
        
        # Cleanup if created
        if os.path.exists("test_graph.png"):
            os.remove("test_graph.png")

    def test_drift_visualizer(self):
        viz = ClockDriftVisualizer()
        viz.add_reading("n1", 0, 0)
        viz.add_reading("n1", 1, 1.1)
        
        viz.plot("test_drift.png")
        
        if os.path.exists("test_drift.png"):
            os.remove("test_drift.png")

if __name__ == '__main__':
    unittest.main()
