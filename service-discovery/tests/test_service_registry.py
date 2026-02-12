import unittest
import time
import threading
import concurrent.futures
from unittest.mock import MagicMock, patch
from src.service_registry import ServiceRegistry, ServiceInstance, ServiceStatus, LoadBalancer

class TestServiceRegistry(unittest.TestCase):
    def setUp(self):
        # fast health check interval for testing
        self.registry = ServiceRegistry(health_check_interval=0.1, max_workers=5)

    def tearDown(self):
        self.registry.stop()

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.registry.register("", "host", 80)
        with self.assertRaises(ValueError):
            self.registry.register("service", "", 80)
        with self.assertRaises(ValueError):
            self.registry.register("service", "host", 0)
        with self.assertRaises(ValueError):
            self.registry.register("service", "host", 70000)

    def test_stop(self):
        # Ensure thread stops
        self.assertTrue(self.registry.health_check_thread.is_alive())
        self.registry.stop()
        self.assertFalse(self.registry.health_check_thread.is_alive())

    def test_register_and_discover(self):
        instance_id = self.registry.register("test-service", "localhost", 8080)
        self.assertIsNotNone(instance_id)
        
        instances = self.registry.discover("test-service")
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].instance_id, instance_id)
        self.assertEqual(instances[0].host, "localhost")
        self.assertEqual(instances[0].port, 8080)
        
        # Ensure it's a copy
        instances[0].host = "hacked"
        original = self.registry.discover("test-service")[0]
        self.assertEqual(original.host, "localhost")

    def test_deregister(self):
        instance_id = self.registry.register("test-service", "localhost", 8080)
        success = self.registry.deregister("test-service", instance_id)
        self.assertTrue(success)
        
        instances = self.registry.discover("test-service")
        self.assertEqual(len(instances), 0)

    def test_heartbeat_and_expiry(self):
        instance_id = self.registry.register("test-service", "localhost", 8080)
        
        # Verify it's there
        self.assertEqual(len(self.registry.discover("test-service")), 1)
        
        # Manually manipulate last_heartbeat to simulate expiry
        with self.registry.lock:
            instance = self.registry.services["test-service"][0]
            instance.last_heartbeat = time.time() - 61 # older than default 60s timeout
            
        # Should not be discovered now (discover checks heartbeat validity)
        self.assertEqual(len(self.registry.discover("test-service")), 0)
        
        # Send heartbeat
        self.registry.heartbeat("test-service", instance_id)
        
        # Should be discovered again
        self.assertEqual(len(self.registry.discover("test-service")), 1)

    def test_load_balancer(self):
        lb = LoadBalancer(self.registry)
        self.registry.register("service-a", "host1", 80)
        self.registry.register("service-a", "host2", 80)
        
        # Round robin check
        inst1 = lb.get_instance("service-a")
        inst2 = lb.get_instance("service-a")
        inst3 = lb.get_instance("service-a")
        
        self.assertIsNotNone(inst1)
        self.assertIsNotNone(inst2)
        self.assertIsNotNone(inst3)
        
        hosts = [inst1.host, inst2.host]
        self.assertIn("host1", hosts)
        self.assertIn("host2", hosts)
        self.assertNotEqual(inst1.host, inst2.host) # Should rotate
        self.assertEqual(inst1.host, inst3.host) # Should wrap around

    def test_stats(self):
        self.registry.register("s1", "h1", 1)
        self.registry.register("s2", "h2", 2)
        stats = self.registry.get_stats()
        self.assertEqual(stats["registrations"], 2)
        self.assertEqual(stats["services"], 2)
        self.assertEqual(stats["total_instances"], 2)

    @patch('urllib.request.urlopen')
    def test_probe_health(self, mock_urlopen):
        # Setup mock for success
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        instance_id = self.registry.register(
            "health-service", 
            "localhost", 
            8080, 
            health_check_url="/health"
        )
        
        # Access internal instance for testing internal method
        with self.registry.lock:
            instance = self.registry.services["health-service"][0]
        
        # Test _probe_health direct call
        is_healthy = self.registry._probe_health(instance)
        self.assertTrue(is_healthy)
        mock_urlopen.assert_called_with("http://localhost:8080/health", timeout=5.0)

        # Setup mock for failure
        mock_urlopen.side_effect = Exception("Connection refused")
        is_healthy = self.registry._probe_health(instance)
        self.assertFalse(is_healthy)

    def test_discover_status_check(self):
        instance_id = self.registry.register("status-service", "localhost", 8080)
        
        self.assertEqual(len(self.registry.discover("status-service")), 1)
        
        with self.registry.lock:
            instance = self.registry.services["status-service"][0]
            instance.status = ServiceStatus.DOWN
            
        self.assertEqual(len(self.registry.discover("status-service")), 0)
        
        with self.registry.lock:
            instance.status = ServiceStatus.UP
            
        self.assertEqual(len(self.registry.discover("status-service")), 1)

    def test_observers(self):
        # Create a mock observer
        observer = MagicMock()
        self.registry.add_observer(observer)
        
        instance_id = self.registry.register(
            "obs-service", "localhost", 9090, health_check_url="/health"
        )
        
        # Access instance
        with self.registry.lock:
            instance = self.registry.services["obs-service"][0]
        
        # Manually trigger status change via _check_single_instance logic or directly
        # Let's use _check_single_instance with a mocked probe to force status change
        
        # Mock probe to return False (DOWN)
        with patch.object(self.registry, '_probe_health', return_value=False):
             self.registry._check_single_instance(instance)
             
        # Check if observer was called
        observer.assert_called_with(instance, ServiceStatus.DOWN)
        self.assertEqual(instance.status, ServiceStatus.DOWN)
        
        observer.reset_mock()
        
        # Mock probe to return True (UP)
        with patch.object(self.registry, '_probe_health', return_value=True):
             self.registry._check_single_instance(instance)
             
        observer.assert_called_with(instance, ServiceStatus.UP)
        self.assertEqual(instance.status, ServiceStatus.UP)

    def test_concurrent_health_checks(self):
        # Register multiple services
        for i in range(10):
            self.registry.register(f"svc-{i}", "localhost", 8000+i, health_check_url="/health")
            
        # Mock _probe_health to take some time but return True
        def slow_probe(instance):
            time.sleep(0.05) # 50ms
            return True
            
        with patch.object(self.registry, '_probe_health', side_effect=slow_probe):
            start = time.time()
            self.registry._run_health_checks()
            duration = time.time() - start
            
            # 10 services * 0.05s = 0.5s if sequential
            # with 5 workers, it should be around 0.1s + overhead
            # We verify it's faster than sequential (0.5s)
            self.assertLess(duration, 0.4, "Health checks should be concurrent")
            
            # Verify stats
            stats = self.registry.get_stats()
            self.assertEqual(stats["health_checks"], 10)

if __name__ == "__main__":
    unittest.main()