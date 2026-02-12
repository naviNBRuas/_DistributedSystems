"""
Transport Interface for Leader Election

Defines the contract for message passing between nodes.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

class Transport(ABC):
    """
    Abstract base class for transport layer.
    
    Users of the library should implement this class to provide
    actual network communication (e.g., via TCP/UDP, HTTP, or message queues).
    """
    
    @abstractmethod
    def send(self, target_id: str, message: Any):
        """
        Send a message to a specific node.
        
        Args:
            target_id: ID of the destination node
            message: Message payload (should be serializable)
        """
        pass
    
    @abstractmethod
    def broadcast(self, message: Any):
        """
        Send a message to all other nodes.
        
        Args:
            message: Message payload
        """
        pass
    
    @abstractmethod
    def set_on_message(self, callback: Callable[[Any], None]):
        """
        Register a callback to handle incoming messages.
        
        Args:
            callback: Function that takes (message) as argument
        """
        pass
    
    @abstractmethod
    def start(self):
        """Start the transport layer (e.g. start listening)"""
        pass
        
    @abstractmethod
    def stop(self):
        """Stop the transport layer"""
        pass
