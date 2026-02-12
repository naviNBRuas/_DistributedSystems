from abc import ABC, abstractmethod
from typing import List, Callable, Any
from dataclasses import dataclass
from storage import LogEntry

class RPCProvider(ABC):
    """
    Abstract interface for Raft RPC communication.
    Implementations (TCP, HTTP, In-Memory) must inherit from this.
    """
    
    @abstractmethod
    def start(self, node):
        """Start the RPC server/listener and register the node to handle requests"""
        pass
        
    @abstractmethod
    def stop(self):
        """Stop the RPC server"""
        pass
    
    @abstractmethod
    def send_request_vote(self, target_node_id: str, term: int, candidate_id: str, 
                         last_log_index: int, last_log_term: int) -> tuple[int, bool]:
        """Send RequestVote RPC and return (term, vote_granted)"""
        pass
        
    @abstractmethod
    def send_append_entries(self, target_node_id: str, term: int, leader_id: str,
                           prev_log_index: int, prev_log_term: int,
                           entries: List[LogEntry], leader_commit: int) -> tuple[int, bool]:
        """Send AppendEntries RPC and return (term, success)"""
        pass

class InMemoryRPC(RPCProvider):
    """
    In-memory RPC implementation for testing/simulation.
    Nodes must be manually registered to the registry.
    """
    
    def __init__(self, registry: dict, disconnected_nodes: set = None):
        self.registry = registry # Shared dict mapping node_id -> RaftNode
        self.node = None
        self.disconnected_nodes = disconnected_nodes if disconnected_nodes is not None else set()
        
    def start(self, node):
        self.node = node
        self.registry[node.node_id] = node
        
    def stop(self):
        if self.node and self.node.node_id in self.registry:
            del self.registry[self.node.node_id]
            
    def disconnect(self, node_id):
        """Simulate network disconnection for a node"""
        self.disconnected_nodes.add(node_id)
        
    def reconnect(self, node_id):
        """Restore network connection"""
        if node_id in self.disconnected_nodes:
            self.disconnected_nodes.remove(node_id)
            
    def send_request_vote(self, target_node_id: str, term: int, candidate_id: str,
                         last_log_index: int, last_log_term: int) -> tuple[int, bool]:
        # Check if sender or receiver is disconnected
        if self.node.node_id in self.disconnected_nodes or target_node_id in self.disconnected_nodes:
            return 0, False
            
        target = self.registry.get(target_node_id)
        if not target:
            # Simulate network failure or node down
            return 0, False 
        return target.handle_request_vote(term, candidate_id, last_log_index, last_log_term)
        
    def send_append_entries(self, target_node_id: str, term: int, leader_id: str,
                           prev_log_index: int, prev_log_term: int,
                           entries: List[LogEntry], leader_commit: int) -> tuple[int, bool]:
        # Check if sender or receiver is disconnected
        if self.node.node_id in self.disconnected_nodes or target_node_id in self.disconnected_nodes:
            return 0, False
            
        target = self.registry.get(target_node_id)
        if not target:
            return 0, False
        return target.handle_append_entries(term, leader_id, prev_log_index, prev_log_term, entries, leader_commit)
