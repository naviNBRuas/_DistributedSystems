"""
Local In-Memory Transport for Testing/Simulation
"""

import threading
import queue
import logging
import time
from typing import Any, Callable, Dict, Optional

from transport import Transport

logger = logging.getLogger(__name__)

class LocalNetwork:
    """
    Singleton-like network bus for local transport.
    Connects multiple LocalTransport instances.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalNetwork, cls).__new__(cls)
                cls._instance.nodes = {}  # id -> callback
                cls._instance.lock = threading.RLock()
        return cls._instance
    
    def register(self, node_id: str, callback: Callable[[Any], None]):
        with self.lock:
            self.nodes[node_id] = callback
            
    def unregister(self, node_id: str):
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                
    def send(self, sender_id: str, target_id: str, message: Any):
        # Simulate network delay?
        # For now, immediate delivery via thread dispatch or queue
        with self.lock:
            target = self.nodes.get(target_id)
            
        if target:
            # We deliver in a separate thread to simulate async network
            # and prevent deadlock if the callback takes locks
            threading.Thread(target=target, args=(message,), daemon=True).start()
        else:
            logger.warning(f"Network: Node {target_id} not found (sender: {sender_id})")

class LocalTransport(Transport):
    """
    In-memory transport for testing.
    Uses a shared LocalNetwork instance to route messages.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.network = LocalNetwork()
        self.callback: Optional[Callable[[Any], None]] = None
        self.running = False
        
    def send(self, target_id: str, message: Any):
        if not self.running:
            return
        self.network.send(self.node_id, target_id, message)
    
    def broadcast(self, message: Any):
        # Not efficient, but works for local test
        with self.network.lock:
            all_nodes = list(self.network.nodes.keys())
            
        for node in all_nodes:
            if node != self.node_id:
                self.send(node, message)
    
    def set_on_message(self, callback: Callable[[Any], None]):
        self.callback = callback
    
    def _receive(self, message: Any):
        if self.running and self.callback:
            try:
                self.callback(message)
            except Exception as e:
                logger.error(f"Error in transport callback for {self.node_id}: {e}", exc_info=True)

    def start(self):
        self.running = True
        self.network.register(self.node_id, self._receive)
        
    def stop(self):
        self.running = False
        self.network.unregister(self.node_id)
