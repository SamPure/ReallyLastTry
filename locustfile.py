from locust import HttpUser, task, between
import json
import random

class APIUser(HttpUser):
    """Simulates a user interacting with the API."""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize user session."""
        self.client.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @task(3)
    def health_check(self):
        """Test health endpoint (high frequency)."""
        self.client.get("/health")

    @task(2)
    def ready_check(self):
        """Test readiness endpoint (medium frequency)."""
        self.client.get("/ready")

    @task(1)
    def metrics(self):
        """Test metrics endpoint (low frequency)."""
        self.client.get("/metrics")

    @task(2)
    def root_endpoint(self):
        """Test root endpoint (medium frequency)."""
        self.client.get("/")

    @task(1)
    def batch_processing(self):
        """Test batch processing endpoint (low frequency)."""
        # Simulate batch data
        data = {
            "items": [
                {"id": i, "value": random.randint(1, 100)}
                for i in range(10)
            ]
        }
        self.client.post("/batch", json=data)

    @task(1)
    def error_handling(self):
        """Test error handling (low frequency)."""
        # Test with invalid data
        self.client.post("/batch", json={"invalid": "data"})

    @task(1)
    def concurrent_requests(self):
        """Test concurrent requests (low frequency)."""
        # Simulate multiple concurrent requests
        self.client.get("/health")
        self.client.get("/ready")
        self.client.get("/metrics")

class LoadTest(HttpUser):
    """Simulates high load on the API."""
    wait_time = between(0.1, 0.5)  # Very short wait time for high load

    @task(10)
    def health_check(self):
        """Test health endpoint under load."""
        self.client.get("/health")

    @task(5)
    def ready_check(self):
        """Test readiness endpoint under load."""
        self.client.get("/ready")

    @task(1)
    def metrics(self):
        """Test metrics endpoint under load."""
        self.client.get("/metrics")
