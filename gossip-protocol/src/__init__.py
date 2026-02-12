"""
gossip-protocol - DistributedSystems Module
Version: 0.1.0
"""

from .gossip_node import GossipNode, GossipMode
from .config import GossipConfig

__version__ = "0.1.0"
__all__ = ["GossipNode", "GossipMode", "GossipConfig"]