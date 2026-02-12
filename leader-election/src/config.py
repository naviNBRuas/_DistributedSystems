"""
Configuration for Leader Election
"""

# Timing defaults (milliseconds)
DEFAULT_ELECTION_TIMEOUT = 5000
DEFAULT_HEARTBEAT_INTERVAL = 1000
DEFAULT_LEASE_DURATION = 10  # seconds

# Quorum
DEFAULT_QUORUM_SIZE = 3

# Limits
MAX_ELECTION_ROUNDS = 10


class ElectionConfig:
    """Configuration for election algorithms"""
    
    def __init__(
        self,
        election_timeout: int = DEFAULT_ELECTION_TIMEOUT,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        lease_duration: int = DEFAULT_LEASE_DURATION,
        quorum_size: int = DEFAULT_QUORUM_SIZE,
        max_election_rounds: int = MAX_ELECTION_ROUNDS,
    ):
        self.election_timeout = election_timeout / 1000.0  # Convert to seconds
        self.heartbeat_interval = heartbeat_interval / 1000.0
        self.lease_duration = lease_duration
        self.quorum_size = quorum_size
        self.max_election_rounds = max_election_rounds
        
        # Validation
        assert self.heartbeat_interval < self.election_timeout, \
            "Heartbeat interval must be less than election timeout"
        assert self.quorum_size > 0, "Quorum size must be positive"
