from abc import ABC, abstractmethod
from typing import List, Any
import collections

class Network(ABC):
    @abstractmethod
    def send(self, message: Any, destination: int):
        pass

    @abstractmethod
    def broadcast(self, message: Any, source: int):
        pass

class InMemoryNetwork(Network):
    def __init__(self):
        self.nodes = {}
        self.message_queue = collections.deque()
        
    def register_node(self, node):
        self.nodes[node.node_id] = node
        
    def send(self, message: Any, destination: int):
        if destination in self.nodes:
            # Direct delivery simulation
            self.nodes[destination].receive(message)
            
    def broadcast(self, message: Any, source: int):
        for node_id, node in self.nodes.items():
            if node_id != source:
                node.receive(message)
