"""
Example: Distributed Transaction with Fencing Tokens

Demonstrates using FencedLock to ensure safety in distributed operations.
Uses fencing tokens to reject writes from stale lock holders.
"""

from src.distributed_lock import DistributedLock
from src.fencing_tokens import FencedLock

class MockDatabase:
    def __init__(self):
        self.data = {}
        self.last_token = 0
        
    def write(self, key, value, fencing_token):
        """
        Write to DB only if fencing_token > last_seen_token
        """
        if fencing_token.value <= self.last_token:
            print(f"DB REJECT: Stale token {fencing_token.value} (current: {self.last_token})")
            return False
            
        self.data[key] = value
        self.last_token = fencing_token.value
        print(f"DB WRITE: {key}={value} (token: {fencing_token.value})")
        return True

def main():
    # Shared resource
    db = MockDatabase()
    
    # Create a lock wrapped with fencing capabilities
    base_lock = DistributedLock("db:transaction", ttl_sec=5)
    fenced_lock = FencedLock(base_lock)
    
    print("--- Client 1 ---")
    token1 = fenced_lock.acquire_with_token()
    if token1:
        print(f"Client 1 acquired lock with token {token1}")
        
        # Simulate a long GC pause or network delay for Client 1
        print("Client 1 paused (GC)...")
        
        print("\n--- Client 2 ---")
        # Client 2 comes in
        # Note: In this local simulation, Client 2 can't acquire if Client 1 holds it
        # unless Client 1 expires. Let's assume Client 1 expired or we force release.
        # For demo, we manually release Client 1's lock "under the hood" to simulate expiry
        base_lock.release() 
        
        token2 = fenced_lock.acquire_with_token()
        print(f"Client 2 acquired lock with token {token2}")
        db.write("record", "updated_by_client_2", token2)
        fenced_lock.release()
        
        print("\n--- Client 1 Resumes ---")
        # Client 1 wakes up and tries to write
        print("Client 1 tries to write with old token...")
        success = db.write("record", "overwritten_by_client_1", token1)
        
        if not success:
            print("Client 1 write blocked by fencing!")
        else:
            print("ERROR: Client 1 overwrite should have failed!")
            
    else:
        print("Client 1 failed to acquire lock")

if __name__ == "__main__":
    main()
