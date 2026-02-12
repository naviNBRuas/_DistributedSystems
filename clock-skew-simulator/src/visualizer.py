"""
Event Graph Visualizer

Visualizes events and their causal relationships using
matplotlib and networkx (if available).
"""

import os
from typing import List, Tuple, Any

# Optional dependencies
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False


class EventGraphVisualizer:
    """
    Visualizes distributed system events as a directed acyclic graph (DAG).
    Nodes are events, edges represent causal links (happens-before).
    """
    
    def __init__(self):
        self.events: List[Tuple[str, Any, str]] = []  # (id, time, type)
        self.edges: List[Tuple[str, str]] = []  # (from, to)
        
    def add_event(self, event_id: str, timestamp: Any, event_type: str = "local"):
        """
        Add an event to the visualization
        
        Args:
            event_id: Unique label for the event
            timestamp: Logical time of the event
            event_type: 'send', 'receive', or 'local'
        """
        self.events.append((event_id, timestamp, event_type))
        
    def add_happens_before(self, from_event: str, to_event: str):
        """
        Add a causal link between events
        
        Args:
            from_event: The causing event
            to_event: The resulting event
        """
        self.edges.append((from_event, to_event))
        
    def render(self, output_path: str = "event_graph.png"):
        """
        Render the graph to a file
        
        Args:
            output_path: Path to save the image (e.g., 'graph.png')
        """
        if not HAS_VISUALIZATION:
            print(f"Warning: Visualization dependencies (matplotlib, networkx) not found.")
            print(f"Cannot render to {output_path}")
            print("Graph structure:")
            for u, v in self.edges:
                print(f"  {u} -> {v}")
            return
            
        G = nx.DiGraph()
        
        # Add nodes
        for eid, ts, etype in self.events:
            label = f"{eid}\n({ts})"
            color = 'skyblue'
            if etype == 'send':
                color = 'lightgreen'
            elif etype == 'receive':
                color = 'salmon'
                
            G.add_node(eid, label=label, color=color)
            
        # Add edges
        G.add_edges_from(self.edges)
        
        # Layout
        pos = nx.spring_layout(G)
        
        # Draw
        plt.figure(figsize=(10, 8))
        
        # Draw nodes
        node_colors = [nx.get_node_attributes(G, 'color').get(n, 'skyblue') for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000, alpha=0.9)
        
        # Draw labels
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=20)
        
        plt.title("Event Causality Graph")
        plt.axis('off')
        
        # Save
        plt.savefig(output_path)
        plt.close()
        print(f"Graph saved to {output_path}")


class ClockDriftVisualizer:
    """
    Visualizes clock drift over time compared to true time.
    """
    
    def __init__(self):
        self.readings = {} # {node_id: [(time, reading), ...]}`
        
    def add_reading(self, node_id: str, timestamp: float, reading: float):
        """
        Add a clock reading point
        
        Args:
            node_id: Node identifier
            timestamp: True physical time
            reading: Clock reading
        """
        if node_id not in self.readings:
            self.readings[node_id] = []
        self.readings[node_id].append((timestamp, reading))
        
    def plot(self, output_path: str = "clock_drift.png"):
        """
        Plot drift lines
        """
        if not HAS_VISUALIZATION:
            print("Warning: Visualization dependencies not found.")
            return

        plt.figure(figsize=(10, 6))
        
        for node_id, data in self.readings.items():
            if not data:
                continue
                
            times, readings = zip(*data)
            # Calculate drift (reading - true_time)
            drifts = [r - t for t, r in data]
            
            plt.plot(times, drifts, label=f"Node {node_id}")
            
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, label="True Time")
        plt.xlabel("True Time (s)")
        plt.ylabel("Clock Skew (s)")
        plt.title("Clock Drift Over Time")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.savefig(output_path)
        plt.close()
        print(f"Drift plot saved to {output_path}")
