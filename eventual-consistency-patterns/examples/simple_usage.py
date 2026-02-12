import sys
import os
import time

# Ensure we can import the package
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from eventual_consistency import ReadRepair, Replica, VersionedValue, CausalSession, VectorClock

# 1. Mock Replicas
class InMemoryReplica:
    def __init__(self, name, data=None):
        self.name = name
        self.store = data if data else {}
    
    def get(self, key):
        print(f"[{self.name}] GET {key}")
        return self.store.get(key)
    
    def put(self, key, value):
        print(f"[{self.name}] PUT {key} = {value.value} (@{value.timestamp})")
        self.store[key] = value

# Setup replicas with some inconsistency
r1 = InMemoryReplica("Node1", {"user:1": VersionedValue("Alice", timestamp=100)})
r2 = InMemoryReplica("Node2", {"user:1": VersionedValue("Alice Updated", timestamp=200)})
r3 = InMemoryReplica("Node3", {}) # Missing data

# 2. Read Repair
print("--- Read Repair ---")
repair = ReadRepair([r1, r2, r3])
value = repair.read("user:1")
print(f"Read Result: {value.value}")

# Wait for async repair
repair.shutdown()
print("Repairs completed.")

# Verify repair
print(f"Node1 value: {r1.store['user:1'].value}")
print(f"Node3 value: {r3.store['user:1'].value}")

# 3. Causal Consistency
print("\n--- Causal Consistency ---")
session = CausalSession("client_A")
v1 = VersionedValue("Post 1", vector_clock=VectorClock({"node1": 1}))

# Simulate reading a value
if session.check_consistency(v1):
    print("Value is consistent, processing...")
    session.update_clock(v1.vector_clock)
else:
    print("Value is stale!")

# Prepare a write
write_clock = session.prepare_write()
print(f"Client clock for new write: {write_clock.clock}")
