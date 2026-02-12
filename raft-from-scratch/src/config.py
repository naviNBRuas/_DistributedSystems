"""
Configuration and Constants for Raft Implementation
"""

# Timing defaults (milliseconds)
DEFAULT_ELECTION_TIMEOUT_MIN = 150
DEFAULT_ELECTION_TIMEOUT_MAX = 300
DEFAULT_HEARTBEAT_INTERVAL = 50

# Log compaction
DEFAULT_SNAPSHOT_INTERVAL = 10000  # entries before snapshot
MAX_LOG_ENTRIES_PER_REQUEST = 100

# Cluster defaults
MIN_CLUSTER_SIZE = 3
RECOMMENDED_CLUSTER_SIZE = 5

# RPC timeouts
RPC_TIMEOUT = 100  # milliseconds

class RaftConfig:
    """Configuration object for Raft nodes"""
    
    def __init__(
        self,
        election_timeout_min: int = DEFAULT_ELECTION_TIMEOUT_MIN,
        election_timeout_max: int = DEFAULT_ELECTION_TIMEOUT_MAX,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
        max_log_entries_per_request: int = MAX_LOG_ENTRIES_PER_REQUEST,
    ):
        self.election_timeout_min = election_timeout_min
        self.election_timeout_max = election_timeout_max
        self.heartbeat_interval = heartbeat_interval
        self.snapshot_interval = snapshot_interval
        self.max_log_entries_per_request = max_log_entries_per_request
        
        # Validation
        assert heartbeat_interval < election_timeout_min, \
            "Heartbeat interval must be less than election timeout"
        assert election_timeout_max > election_timeout_min, \
            "Max timeout must be greater than min timeout"
