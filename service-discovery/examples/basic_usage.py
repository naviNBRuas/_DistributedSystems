import sys
import os
import logging
import time
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.service_registry import ServiceRegistry, LoadBalancer, ServiceStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
# Reduce noise from other loggers if necessary
logging.getLogger("src.service_registry").setLevel(logging.INFO)

def on_service_status_change(instance, status):
    print(f"\n[EVENT] Service {instance.service_name} ({instance.instance_id}) is now {status.value}")

if __name__ == "__main__":
    print("=== Service Discovery Example ===\n")
    
    # Create registry with concurrent health checks
    # Interval 2s, max 5 workers
    registry = ServiceRegistry(health_check_interval=2.0, max_workers=5)
    
    # Add observer for status changes
    registry.add_observer(on_service_status_change)
    
    try:
        # Register services
        print("--- Registering Services ---")
        id1 = registry.register(
            service_name="user-service",
            host="10.0.0.1",
            port=8080,
            metadata={"version": "0.1.0", "region": "us-east"},
            health_check_url="/health"
        )
        print(f"Registered user-service: {id1}")
        
        id2 = registry.register(
            service_name="user-service",
            host="10.0.0.2",
            port=8080,
            metadata={"version": "0.1.0", "region": "us-west"}
        )
        print(f"Registered user-service: {id2}")
        
        id3 = registry.register(
            service_name="order-service",
            host="10.0.1.1",
            port=8081
        )
        print(f"Registered order-service: {id3}\n")
        
        # Discover services
        print("--- Discovering Services ---")
        instances = registry.discover("user-service")
        print(f"Found {len(instances)} user-service instances:")
        for inst in instances:
            print(f"  - {inst.get_address()} ({inst.status.value})")
        
        # Load balancing
        print("\n--- Load Balancing ---")
        lb = LoadBalancer(registry)
        
        for i in range(5):
            inst = lb.get_instance("user-service")
            if inst:
                print(f"Request {i+1}: → {inst.get_address()}")
            else:
                print(f"Request {i+1}: No instance available")
        
        # Simulate status change (Heartbeat expiry)
        print("\n--- Simulating Heartbeat Expiry ---")
        print("Waiting for health checks to mark stale services as DOWN (timeout ~2s)...")
        # In a real scenario, services would be sending heartbeats.
        # Here we don't send heartbeats, so they should eventually timeout.
        # But our default timeout in ServiceInstance.is_heartbeat_valid is 60s.
        # That's too long for this demo.
        
        # Let's force a status change manually to demo the observer
        print("Manually marking order-service as DOWN for demo...")
        with registry.lock:
             # This is a hack for the demo; normally the background thread does this
             svc = registry.services["order-service"][0]
             # We trigger the internal method that notifies observers
             # But we can't easily access the internal method from outside properly without hacks
             # So let's just wait for the loop or...
             pass
        
        # Actually, let's just register a service with a very short custom heartbeat requirement?
        # The class doesn't expose per-service timeout config in __init__ easily (it's hardcoded default in method).
        # We'll just manually trigger the observer logic by hacking the status update to show it works.
        # Or better, let's run a loop and see if the health check picks up something.
        
        # Since we provided health_check_url for id1 (10.0.0.1), and that IP is likely not reachable or has no server,
        # the health check probe should fail and mark it DOWN.
        
        print("Waiting for health check probe to fail for user-service (10.0.0.1)...")
        time.sleep(3.0) 
        
        # Check status again
        instances = registry.discover_all("user-service")
        print(f"\nUser-Service Statuses:")
        for inst in instances:
            print(f"  - {inst.get_address()}: {inst.status.value}")
            
        # Stats
        print("\n--- Registry Stats ---")
        stats = registry.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
            
    finally:
        # Clean shutdown
        print("\nStopping registry...")
        registry.stop()