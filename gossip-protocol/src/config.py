"""
Configuration for Gossip Protocol
"""

# Timing defaults (milliseconds)
DEFAULT_GOSSIP_INTERVAL = 1000
DEFAULT_MEMBERSHIP_GOSSIP_INTERVAL = 500
DEFAULT_FAILURE_DETECTION_INTERVAL = 1000

# Protocol parameters
DEFAULT_GOSSIP_FANOUT = 3
DEFAULT_MAX_TRANSMISSION_COUNT = 3

# Failure detection
DEFAULT_SUSPICION_TIMEOUT = 5000  # milliseconds
DEFAULT_PHI_THRESHOLD = 8.0  # Phi value for failure detection

# State management
DEFAULT_STATE_TTL = 86400  # 24 hours in seconds
MAX_STATE_SIZE = 10000  # Maximum number of entries


class GossipConfig:
    """Configuration object for gossip nodes"""
    
    def __init__(
        self,
        gossip_interval: int = DEFAULT_GOSSIP_INTERVAL,
        gossip_fanout: int = DEFAULT_GOSSIP_FANOUT,
        membership_gossip_interval: int = DEFAULT_MEMBERSHIP_GOSSIP_INTERVAL,
        failure_detection_interval: int = DEFAULT_FAILURE_DETECTION_INTERVAL,
        suspicion_timeout: int = DEFAULT_SUSPICION_TIMEOUT,
        max_transmission_count: int = DEFAULT_MAX_TRANSMISSION_COUNT,
        phi_threshold: float = DEFAULT_PHI_THRESHOLD,
    ):
        self.gossip_interval = gossip_interval
        self.gossip_fanout = gossip_fanout
        self.membership_gossip_interval = membership_gossip_interval
        self.failure_detection_interval = failure_detection_interval
        self.suspicion_timeout = suspicion_timeout
        self.max_transmission_count = max_transmission_count
        self.phi_threshold = phi_threshold
        
        # Validation
        assert gossip_fanout > 0, "Fanout must be positive"
        assert gossip_interval > 0, "Gossip interval must be positive"
