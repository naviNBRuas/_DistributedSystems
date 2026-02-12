"""
Example: Leader Protected Coordination

Demonstrates using a lock for leader election/coordination.
Only the process holding the lock acts as the 'leader' to perform tasks.
"""

import time
import sys
from src.lease_lock import LeaseLock

class ServiceNode:
    def __init__(self, node_id):
        self.node_id = node_id
        self.is_running = True
        # In a real scenario, this would use a shared backend like ZooKeeper
        self.leader_lock = LeaseLock("service:leader", duration=2.0)
        
    def run(self):
        print(f"Node {self.node_id} starting...")
        while self.is_running:
            if self.leader_lock.acquire():
                print(f"Node {self.node_id} is LEADER. Performing leader tasks...")
                
                # Simulate doing leader work for a while
                for _ in range(5):
                    if not self.is_running: break
                    print(f"Node {self.node_id} (Leader) heartbeat...")
                    
                    # Must renew lease to keep leadership
                    if not self.leader_lock.renew():
                        print(f"Node {self.node_id} lost leadership (failed renew)!")
                        break
                    time.sleep(0.5)
                
                print(f"Node {self.node_id} stepping down.")
                self.leader_lock.release()
                time.sleep(1) # Wait before trying again
            else:
                print(f"Node {self.node_id} is FOLLOWER. Waiting...")
                time.sleep(1)

    def stop(self):
        self.is_running = False

if __name__ == "__main__":
    # Simulate a single node for demonstration
    # In reality, run multiple instances of this script
    node = ServiceNode(node_id="node-1")
    try:
        # Run for 10 seconds
        import threading
        t = threading.Thread(target=node.run)
        t.start()
        time.sleep(10)
        node.stop()
        t.join()
    except KeyboardInterrupt:
        node.stop()
