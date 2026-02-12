"""
Example: Distributed Counter using Raft

This example demonstrates a simple distributed counter that
maintains consistency across multiple nodes.

For demonstration, this example runs a 3-node cluster within a single process
using InMemoryRPC and threads.
"""

import sys
import os
import shutil
import tempfile
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from raft_node import RaftNode
from state_machine import CounterStateMachine
from rpc import InMemoryRPC
from storage import FileStorage
from config import RaftConfig


class DistributedCounter:
    """Fault-tolerant distributed counter using Raft"""
    
    def __init__(self, node_id: str, peers: list[str], registry: dict, storage_dir: str):
        self.state_machine = CounterStateMachine()
        self.storage = FileStorage(os.path.join(storage_dir, node_id), node_id)
        self.rpc = InMemoryRPC(registry)
        
        self.node = RaftNode(
            node_id=node_id,
            peers=peers,
            state_machine=self.state_machine,
            storage=self.storage,
            rpc=self.rpc,
            config=RaftConfig(
                election_timeout_min=200,
                election_timeout_max=400,
                heartbeat_interval=50
            )
        )
        self.node.start()
    
    def increment(self, delta: int = 1) -> bool:
        """Increment the counter by delta"""
        command = {"op": "increment", "delta": delta}
        future = self.node.submit_command(command)
        try:
            result = future.result(timeout=5)
            return result.get("status") == "ok"
        except Exception as e:
            print(f"Error incrementing: {e}")
            return False
    
    def get(self) -> int:
        """Get the current counter value"""
        result = self.node.read_state("")
        return result.get("value", 0) if result else 0
    
    def is_leader(self) -> bool:
        return self.node.is_leader
    
    def stop(self):
        self.node.stop()


def main():
    """Example usage with 3 nodes"""
    
    registry = {}
    test_dir = tempfile.mkdtemp()
    nodes = ["node1", "node2", "node3"]
    counters = []
    
    try:
        print("Starting 3-node cluster...")
        for node_id in nodes:
            peers = [n for n in nodes if n != node_id]
            counter = DistributedCounter(node_id, peers, registry, test_dir)
            counters.append(counter)
            
        print("Waiting for leader election...")
        time.sleep(2)
        
        # Find leader
        leader_counter = next((c for c in counters if c.is_leader()), None)
        
        if leader_counter:
            print(f"Leader is {leader_counter.node.node_id}")
            
            print("Incrementing by 5...")
            if leader_counter.increment(5):
                print("Success")
            
            print("Incrementing by 3...")
            leader_counter.increment(3)
            
            time.sleep(0.5)
            
            # Check consistency
            for counter in counters:
                val = counter.get()
                print(f"Node {counter.node.node_id} value: {val}")
                
        else:
            print("No leader elected!")
            
    finally:
        print("Stopping cluster...")
        for counter in counters:
            counter.stop()
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()