"""
Example: Master-Worker Coordination using Leader Election

This example shows how to use leader election to coordinate
a master-worker pattern where the master assigns work to workers.
"""

import sys
import os
import time
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from election_manager import ElectionManager, Algorithm
from local_transport import LocalTransport

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')


class MasterWorker:
    """
    Master-worker coordination system
    
    The elected leader becomes the master and assigns work to workers.
    Workers process tasks assigned by the master.
    """
    
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        
        # Use LocalTransport for simulation
        self.transport = LocalTransport(node_id)
        
        self.manager = ElectionManager(
            node_id=node_id,
            peers=peers,
            transport=self.transport,
            algorithm=Algorithm.BULLY,
            heartbeat_interval=0.5,
            election_timeout=2.0
        )
        
        # State
        self.assigned_tasks = {}
        
        # Register for leadership changes
        self.manager.on_leader_change(self._on_leadership_change)
        
    def start(self):
        self.manager.start()
    
    def _on_leadership_change(self, new_leader: str):
        """Handle leadership changes"""
        # print(f"[{self.node_id}] Leadership changed to {new_leader}")
        
        if new_leader == self.node_id:
            logging.info(f"[{self.node_id}] I am now the MASTER")
            self._become_master()
        else:
            logging.info(f"[{self.node_id}] I am a WORKER (Master: {new_leader})")
    
    def _become_master(self):
        """Transition to master role"""
        # As master, start assigning work
        pass
    
    def is_master(self) -> bool:
        """Check if this node is the master"""
        return self.manager.is_leader()
    
    def assign_task(self, worker_id: str, task: dict):
        """
        Assign a task to a worker (master only)
        """
        if not self.is_master():
            logging.warning(f"[{self.node_id}] Not master, cannot assign tasks")
            return False
        
        logging.info(f"[{self.node_id}] Assigning task to {worker_id}: {task}")
        # In a real app, send task via transport
        return True
    
    def stop(self):
        """Stop the coordinator"""
        self.manager.stop()


def main():
    """Example usage"""
    
    # Create a 3-node cluster
    node1 = MasterWorker("node1", ["node2", "node3"])
    node2 = MasterWorker("node2", ["node1", "node3"])
    node3 = MasterWorker("node3", ["node1", "node2"])
    
    node1.start()
    node2.start()
    node3.start()
    
    # Wait for election to converge
    print("Waiting for election...")
    time.sleep(3)
    
    # Find the master
    master = None
    for node in [node1, node2, node3]:
        if node.is_master():
            master = node
            break
    
    if master:
        print(f"\n=== Master is {master.node_id} ===")
        
        # Master assigns tasks
        master.assign_task("node2", {"job": "process_batch_1"})
        master.assign_task("node3", {"job": "process_batch_2"})
    else:
        print("\n=== No master elected yet ===")
    
    # Cleanup
    print("\nShutting down...")
    node1.stop()
    node2.stop()
    node3.stop()


if __name__ == "__main__":
    main()
