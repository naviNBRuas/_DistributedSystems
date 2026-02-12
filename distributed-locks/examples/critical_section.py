"""
Example: Critical Section Protection

Demonstrates how to use DistributedLock to protect a critical section
of code, ensuring only one process can execute it at a time.
"""

import time
import random
import threading
from src.distributed_lock import DistributedLock, LockManager

def critical_task(worker_id, lock_manager):
    resource = "database:write_access"
    print(f"Worker {worker_id} attempting to acquire lock...")
    
    # Acquire lock with a timeout (wait up to 5 seconds)
    token = lock_manager.acquire_lock(resource, owner=f"worker-{worker_id}", timeout_sec=5)
    
    if token:
        print(f"Worker {worker_id} ACQUIRED lock. Doing work...")
        try:
            # Simulate critical section work
            duration = random.uniform(0.5, 1.5)
            time.sleep(duration)
            print(f"Worker {worker_id} finishing work.")
        finally:
            lock_manager.release_lock(resource, token)
            print(f"Worker {worker_id} RELEASED lock.")
    else:
        print(f"Worker {worker_id} FAILED to acquire lock (timeout).")

def main():
    manager = LockManager()
    threads = []
    
    print("Starting 5 workers competing for the same resource...")
    
    for i in range(5):
        t = threading.Thread(target=critical_task, args=(i, manager))
        threads.append(t)
        t.start()
        # Stagger starts slightly
        time.sleep(0.1)
        
    for t in threads:
        t.join()
        
    print("All workers finished.")

if __name__ == "__main__":
    main()
