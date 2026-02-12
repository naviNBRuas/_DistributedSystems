"""
Service Discovery Registry

Dynamic service registration, discovery, and health checking
for microservices architectures.
"""

import time
import threading
import uuid
import urllib.request
import urllib.error
import urllib.parse
import logging
import concurrent.futures
import dataclasses
from typing import Dict, List, Optional, Callable, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service instance status"""
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass
class ServiceInstance:
    """Service instance information"""
    service_name: str
    instance_id: str
    host: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.UP
    health_check_url: Optional[str] = None
    health_interval: float = 30.0  # seconds
    last_heartbeat: float = field(default_factory=time.time)
    
    def is_heartbeat_valid(self, timeout: float = 60.0) -> bool:
        """Check if instance heartbeat is within timeout"""
        return time.time() - self.last_heartbeat < timeout
    
    def get_address(self) -> str:
        """Get service address"""
        return f"{self.host}:{self.port}"


class ServiceRegistry:
    """
    Service Registry
    
    Manages service registration, discovery, and health checking.
    """
    
    def __init__(self, health_check_interval: float = 30.0, max_workers: int = 10):
        """
        Initialize service registry
        
        Args:
            health_check_interval: Default interval between health checks
            max_workers: Maximum number of threads for concurrent health checks
        """
        self.health_check_interval = health_check_interval
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.lock = threading.RLock()
        self._stop_event = threading.Event()
        self._observers: List[Callable[[ServiceInstance, ServiceStatus], None]] = []
        
        # Health check thread
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="ServiceRegistry-HealthCheck"
        )
        self.health_check_thread.start()
        
        self.stats = {
            "registrations": 0,
            "deregistrations": 0,
            "health_checks": 0,
            "failed_checks": 0
        }
        self.max_workers = max_workers

    def stop(self):
        """Stop the background health check thread"""
        logger.info("Stopping Service Registry...")
        self._stop_event.set()
        if self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=2.0)
    
    def add_observer(self, callback: Callable[[ServiceInstance, ServiceStatus], None]):
        """
        Add an observer to listen for service status changes.
        Callback signature: (instance: ServiceInstance, new_status: ServiceStatus) -> None
        """
        with self.lock:
            self._observers.append(callback)

    def _notify_observers(self, instance: ServiceInstance, new_status: ServiceStatus):
        """Notify observers of a status change"""
        # Snapshot observers to avoid locking during callbacks
        with self.lock:
            observers_snapshot = list(self._observers)
        
        for callback in observers_snapshot:
            try:
                callback(instance, new_status)
            except Exception as e:
                logger.error(f"Error in service registry observer: {e}")

    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: Optional[Dict] = None,
        health_check_url: Optional[str] = None
    ) -> str:
        """
        Register a service instance
        
        Args:
            service_name: Name of the service
            host: Service host/IP
            port: Service port
            metadata: Optional metadata (version, region, etc.)
            health_check_url: Optional health check endpoint
            
        Returns:
            Instance ID
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not service_name or not service_name.strip():
            raise ValueError("Service name is required")
        if not host or not host.strip():
            raise ValueError("Host is required")
        if not (0 < port < 65536):
            raise ValueError("Port must be between 1 and 65535")
        
        if health_check_url:
            # Basic validation that it looks like a path or URL
            if not (health_check_url.startswith('/') or health_check_url.startswith('http')):
                 # Assuming relative path is allowed and will be appended to host:port
                 pass

        instance_id = str(uuid.uuid4())
        
        with self.lock:
            instance = ServiceInstance(
                service_name=service_name,
                instance_id=instance_id,
                host=host,
                port=port,
                metadata=metadata or {},
                health_check_url=health_check_url,
                health_interval=self.health_check_interval
            )
            
            if service_name not in self.services:
                self.services[service_name] = []
            
            self.services[service_name].append(instance)
            self.stats["registrations"] += 1
        
        logger.info(
            f"[ServiceRegistry] Registered {service_name} instance {instance_id} "
            f"at {host}:{port}"
        )
        
        return instance_id
    
    def deregister(self, service_name: str, instance_id: str) -> bool:
        """
        Deregister a service instance
        
        Args:
            service_name: Name of the service
            instance_id: Instance ID
            
        Returns:
            True if instance was deregistered
        """
        with self.lock:
            if service_name not in self.services:
                return False
            
            # Find and remove instance
            for i, inst in enumerate(self.services[service_name]):
                if inst.instance_id == instance_id:
                    self.services[service_name].pop(i)
                    self.stats["deregistrations"] += 1
                    
                    # Clean up empty service keys
                    if not self.services[service_name]:
                        del self.services[service_name]
                        
                    logger.info(f"[ServiceRegistry] Deregistered {service_name} instance {instance_id}")
                    return True
        
        return False
    
    def discover(self, service_name: str) -> List[ServiceInstance]:
        """
        Discover healthy service instances.
        Returns COPIES of instances to prevent external modification.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of available service instances
        """
        with self.lock:
            if service_name not in self.services:
                return []
            
            # Return only healthy instances
            instances = self.services[service_name]
            # Check both status (active checks) and heartbeat time (passive check)
            # Note: We rely on the background thread to update 'status' based on checks,
            # but we double check heartbeat validity here for immediate feedback.
            healthy = [
                dataclasses.replace(inst) for inst in instances 
                if inst.status == ServiceStatus.UP and inst.is_heartbeat_valid()
            ]
            
            return healthy
    
    def discover_all(self, service_name: str) -> List[ServiceInstance]:
        """
        Get all instances including unhealthy ones.
        Returns COPIES of instances.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of all service instances
        """
        with self.lock:
            return [dataclasses.replace(inst) for inst in self.services.get(service_name, [])]
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """
        Record heartbeat for an instance
        
        Args:
            service_name: Name of the service
            instance_id: Instance ID
            
        Returns:
            True if heartbeat was recorded
        """
        with self.lock:
            if service_name not in self.services:
                return False
            
            for inst in self.services[service_name]:
                if inst.instance_id == instance_id:
                    inst.last_heartbeat = time.time()
                    # If it was DOWN due to missing heartbeat, we might consider bringing it UP
                    # However, if it has a health check URL, we might want to wait for the next check
                    # Or we optimistically set it to UP if it doesn't have a check URL.
                    # Simple strategy: If it sends a heartbeat, it's alive.
                    if inst.status == ServiceStatus.UNKNOWN:
                         inst.status = ServiceStatus.UP
                    elif inst.status == ServiceStatus.DOWN and not inst.health_check_url:
                         # If no active check is failing, heartbeat revives it
                         inst.status = ServiceStatus.UP
                    return True
        
        return False
    
    def _health_check_loop(self):
        """Periodic health check loop"""
        logger.info("Health check loop started")
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self.health_check_interval):
                break
            self._run_health_checks()
    
    def _run_health_checks(self):
        """Run health checks for all instances in parallel"""
        with self.lock:
            # Flatten all instances into a list for processing
            all_instances = [
                inst 
                for instances in self.services.values() 
                for inst in instances
            ]
            
        if not all_instances:
            return

        # Use ThreadPoolExecutor for concurrent checks
        # Limit max_workers to avoid resource exhaustion
        workers = min(len(all_instances), self.max_workers)
        if workers == 0:
            workers = 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_instance = {
                executor.submit(self._check_single_instance, inst): inst 
                for inst in all_instances
            }
            
            for future in concurrent.futures.as_completed(future_to_instance):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected error in health check task: {e}")

    def _check_single_instance(self, instance: ServiceInstance):
        """
        Check health for a single instance and update its status.
        This runs inside the thread pool.
        """
        original_status = instance.status
        new_status = original_status

        # 1. Check Heartbeat (Passive)
        # We give a little buffer to the timeout
        if not instance.is_heartbeat_valid(timeout=60.0):
            new_status = ServiceStatus.DOWN
        else:
            # 2. Check Active Probe (Active)
            if instance.health_check_url:
                is_healthy = self._probe_health(instance)
                new_status = ServiceStatus.UP if is_healthy else ServiceStatus.DOWN
            else:
                # If heartbeat is valid and no active check needed, assume UP
                new_status = ServiceStatus.UP

        # Update status if changed
        if new_status != original_status:
            # We need to be careful modifying the object if another thread is reading it
            # But since we are the only writer to 'status' (mostly), and discover() reads it
            # Atomic assignment is generally safe in Python for basic types
            instance.status = new_status
            logger.info(f"Service {instance.service_name} ({instance.instance_id}) status changed: {original_status.value} -> {new_status.value}")
            self._notify_observers(instance, new_status)
        
        # Update stats
        with self.lock:
            self.stats["health_checks"] += 1
            if new_status == ServiceStatus.DOWN:
                self.stats["failed_checks"] += 1

    def _probe_health(self, instance: ServiceInstance) -> bool:
        """Perform HTTP health check"""
        url = instance.health_check_url
        if not url:
            return True
            
        if not url.startswith("http"):
            url = f"http://{instance.host}:{instance.port}{url}"
            
        try:
            # Set a short timeout for health checks
            with urllib.request.urlopen(url, timeout=5.0) as response:
                return 200 <= response.status < 300
        except Exception as e:
            # Only log verbose if needed, or stick to debug to avoid spam
            logger.debug(f"Health check failed for {instance.instance_id} ({url}): {e}")
            return False
    
    def get_services(self) -> List[str]:
        """Get list of registered services"""
        with self.lock:
            return list(self.services.keys())
    
    def get_stats(self) -> dict:
        """Get registry statistics"""
        with self.lock:
            total_instances = sum(len(inst) for inst in self.services.values())
            healthy_instances = sum(
                len([i for i in inst if i.status == ServiceStatus.UP and i.is_heartbeat_valid()])
                for inst in self.services.values()
            )
            
            return {
                "registrations": self.stats["registrations"],
                "deregistrations": self.stats["deregistrations"],
                "health_checks": self.stats["health_checks"],
                "failed_checks": self.stats["failed_checks"],
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "services": len(self.services)
            }


class LoadBalancer:
    """
    Simple Load Balancer
    
    Routes requests to available service instances.
    """
    
    def __init__(self, registry: ServiceRegistry):
        """
        Initialize load balancer
        
        Args:
            registry: Service registry
        """
        self.registry = registry
        self.current_index: Dict[str, int] = {}  # Round-robin index per service
        self.lock = threading.Lock()
    
    def get_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """
        Get next service instance using round-robin
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance or None if unavailable
        """
        instances = self.registry.discover(service_name)
        
        if not instances:
            # Optional: Log warning only periodically to avoid spam
            return None
        
        with self.lock:
            if service_name not in self.current_index:
                self.current_index[service_name] = 0
            
            idx = self.current_index[service_name]
            instance = instances[idx % len(instances)]
            
            # Update index for next call
            self.current_index[service_name] = (idx + 1) % len(instances)
            
            return instance