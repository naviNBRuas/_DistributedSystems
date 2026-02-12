"""
Network Proxy

Central integration point for all network simulation capabilities.
Combines partitioning, latency, and packet loss.
"""

from typing import Any, Optional
from .partition_coordinator import PartitionCoordinator
from .latency_injector import LatencyInjector
from .packet_dropper import PacketDropper


class NetworkProxy:
    """
    Proxy for handling network communications in tests.
    
    Integrates:
    - PartitionCoordinator (connectivity checks)
    - LatencyInjector (delays)
    - PacketDropper (loss)
    """
    
    def __init__(
        self,
        coordinator: PartitionCoordinator,
        latency_injector: Optional[LatencyInjector] = None,
        packet_dropper: Optional[PacketDropper] = None
    ):
        self.coordinator = coordinator
        self.latency_injector = latency_injector or LatencyInjector()
        self.packet_dropper = packet_dropper or PacketDropper()
        
    def send(self, source: str, target: str, message: Any = None) -> bool:
        """
        Attempt to send a message from source to target.
        
        Returns:
            True if message was delivered (not blocked/dropped)
            False if message failed (partitioned or dropped)
            
        Side Effects:
            - May block for simulated latency
        """
        # 1. Check Connectivity (Partitions & Crashes)
        if not self.coordinator.can_communicate(source, target):
            return False
            
        # 2. Check Packet Loss
        if self.packet_dropper.should_drop(source, target, message):
            return False
            
        # 3. Apply Latency (Blocking)
        # Calculate size if possible
        size = 0
        if message and hasattr(message, '__len__'):
            size = len(message)
            
        self.latency_injector.delay_message(source, target, size)
        
        return True

    def reset(self):
        """Reset all simulation components"""
        self.coordinator.heal_partition()
        for node in self.coordinator.crashed_nodes.copy():
            self.coordinator.recover_node(node)
        self.latency_injector.clear_all()
        self.packet_dropper.clear_all()
