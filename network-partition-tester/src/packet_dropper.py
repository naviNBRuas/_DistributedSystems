"""
Packet Dropper

Simulates network packet loss and reliability issues.
"""

import random
import time
from typing import Dict, Callable, Optional, Any, Set
from dataclasses import dataclass


@dataclass
class BurstLossConfig:
    """Configuration for burst packet loss"""
    start_time: float
    duration: float
    loss_rate: float


class PacketDropper:
    """
    Simulates packet loss in network communication.
    
    Features:
    - Random packet loss (BER/PER)
    - Conditional packet loss (based on message content)
    - Burst loss (temporary high loss rate)
    """
    
    def __init__(self):
        # Loss rates: (source, target) -> rate (0.0 to 1.0)
        self.loss_rates: Dict[tuple, float] = {}
        
        # Conditional drops: list of (condition_fn, rate)
        self.conditional_drops: list[tuple[Callable[[Any], bool], float]] = []
        
        # Burst configurations: (source, target) -> BurstLossConfig
        self.bursts: Dict[tuple, BurstLossConfig] = {}
        
    def set_loss_rate(self, source: str, target: str, loss_rate: float):
        """
        Set packet loss rate between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
            loss_rate: Probability of packet loss (0.0 to 1.0)
        """
        if not 0.0 <= loss_rate <= 1.0:
            raise ValueError("Loss rate must be between 0.0 and 1.0")
            
        self.loss_rates[(source, target)] = loss_rate
        print(f"[PacketDropper] Set loss rate {source} -> {target}: {loss_rate:.1%}")

    def drop_if(self, condition: Callable[[Any], bool], rate: float):
        """
        Conditionally drop packets based on message content.
        
        Args:
            condition: Function taking message and returning bool
            rate: Probability of drop if condition is met
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError("Drop rate must be between 0.0 and 1.0")
            
        self.conditional_drops.append((condition, rate))
        print(f"[PacketDropper] Added conditional drop rule (rate: {rate:.1%})")

    def burst_loss(
        self,
        source: str,
        target: str,
        burst_duration: float,
        loss_rate: float = 1.0
    ):
        """
        Configure a temporary burst of packet loss.
        
        Args:
            source: Source node ID
            target: Target node ID
            burst_duration: Duration of burst in seconds
            loss_rate: Loss rate during burst
        """
        config = BurstLossConfig(
            start_time=time.time(),
            duration=burst_duration,
            loss_rate=loss_rate
        )
        self.bursts[(source, target)] = config
        print(f"[PacketDropper] Scheduled burst loss {source} -> {target} for {burst_duration}s")

    def should_drop(self, source: str, target: str, message: Any = None) -> bool:
        """
        Check if a packet should be dropped based on current rules.
        
        Args:
            source: Source node ID
            target: Target node ID
            message: The message/packet content (optional)
            
        Returns:
            True if packet should be dropped
        """
        current_time = time.time()
        
        # 1. Check burst loss
        burst = self.bursts.get((source, target))
        if burst:
            if current_time - burst.start_time <= burst.duration:
                if random.random() < burst.loss_rate:
                    return True
            else:
                # Burst expired
                del self.bursts[(source, target)]
        
        # 2. Check static loss rate
        base_rate = self.loss_rates.get((source, target), 0.0)
        if base_rate > 0 and random.random() < base_rate:
            return True
            
        # 3. Check conditional drops
        if message is not None:
            for condition, rate in self.conditional_drops:
                if condition(message):
                    if random.random() < rate:
                        return True
                        
        return False
    
    def clear_all(self):
        """Clear all drop rules"""
        self.loss_rates.clear()
        self.conditional_drops.clear()
        self.bursts.clear()
        print("[PacketDropper] Cleared all rules")
