"""
network-partition-tester - DistributedSystems Module
Version: 0.1.0
"""

from .partition_coordinator import PartitionCoordinator, Partition, PartitionState
from .failure_scenarios import (
    FailureScenario,
    SimplePartition,
    NodeIsolation,
    AsymmetricPartition,
    CascadingFailures
)
from .latency_injector import LatencyInjector
from .packet_dropper import PacketDropper
from .network_proxy import NetworkProxy
from .assertions import ClusterAssertions
from .recorder import ScenarioRecorder, ScenarioReplayer

__version__ = "0.1.0"

__all__ = [
    "PartitionCoordinator",
    "Partition",
    "PartitionState",
    "FailureScenario",
    "SimplePartition",
    "NodeIsolation",
    "AsymmetricPartition",
    "CascadingFailures",
    "LatencyInjector",
    "PacketDropper",
    "NetworkProxy",
    "ClusterAssertions",
    "ScenarioRecorder",
    "ScenarioReplayer",
]