"""
Example: Distributed Key-Value Store using Raft

This example shows how to build a linearizable key-value store
on top of the Raft consensus implementation.

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
from state_machine import KeyValueStateMachine
from rpc import InMemoryRPC
from storage import FileStorage
from config import RaftConfig


class RaftKVStore:
    """
    Distributed key-value store with strong consistency
    """
    
    def __init__(self, node_id: str, peers: list[str], registry: dict, storage_dir: str):
        self.state_machine = KeyValueStateMachine()
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
    
    def set(self, key: str, value: any) -> bool:
        """Set a key-value pair"""
        command = {"op": "set", "key": key, "value": value}
        future = self.node.submit_command(command)
        try:
            result = future.result(timeout=5)
            return result.get("status") == "ok"
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False
    
    def get(self, key: str) -> any:
        """Get a value by key"""
        result = self.node.read_state(key)
        return result.get("value") if result else None
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        command = {"op": "delete", "key": key}
        future = self.node.submit_command(command)
        try:
            result = future.result(timeout=5)
            return result.get("deleted")
        except Exception as e:
            print(f"Error deleting {key}: {e}")
            return False
    
    def is_leader(self) -> bool:
        """Check if this node is the current leader"""
        return self.node.is_leader
    
    def stop(self):
        """Stop the node"""
        self.node.stop()


def main():
    """Example usage of RaftKVStore with 3 nodes"""
    
    # Setup
    registry = {}
    test_dir = tempfile.mkdtemp()
    nodes = ["node1", "node2", "node3"]
    stores = []
    
    try:
        print("Starting 3-node cluster...")
        for node_id in nodes:
            peers = [n for n in nodes if n != node_id]
            store = RaftKVStore(node_id, peers, registry, test_dir)
            stores.append(store)
            
        print("Waiting for leader election...")
        time.sleep(2)
        
        # Find leader
        leader_store = next((s for s in stores if s.is_leader()), None)
        
        if leader_store:
            print(f"Leader is {leader_store.node.node_id}")
            
            # Perform operations
            print("Setting key1 = value1")
            if leader_store.set("key1", "value1"):
                print("Success")
            
            print("Setting key2 = value2")
            leader_store.set("key2", "value2")
            
            # Read from all nodes (eventually consistent if reading from followers)
            # In our implementation read_state is local, so followers might be stale.
            time.sleep(0.5) 
            for store in stores:
                val = store.get("key1")
                print(f"Node {store.node.node_id} sees key1 = {val}")
            
            print("Deleting key1")
            leader_store.delete("key1")
            
            time.sleep(0.5)
            val = leader_store.get("key1")
            print(f"Leader sees key1 = {val}")
            
        else:
            print("No leader elected!")
            
    finally:
        print("Stopping cluster...")
        for store in stores:
            store.stop()
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()