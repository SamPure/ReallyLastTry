from locust import HttpUser, task, between, events
import json
import random
import os
from typing import Dict, List

# Environment-specific configurations
ENV = os.getenv("ENV", "development")
HOSTS = {
    "development": "http://localhost:8000",
    "staging": "https://staging-api.example.com",
    "production": "https://api.example.com"
}

class BaseUser(HttpUser):
    """Base user class with common functionality."""
    host = HOSTS[ENV]
    wait_time = between(1, 5)

    def on_start(self):
        """Initialize user session."""
        self.client.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": os.getenv("API_KEY", "test-key")
        }

class APIUser(BaseUser):
    """Simulates regular user interactions with the API."""

    @task(3)
    def health_check(self):
        """Check health endpoints."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

        with self.client.get("/ready", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Ready check failed: {response.status_code}")

    @task(2)
    def metrics_and_root(self):
        """Access metrics and root endpoints."""
        self.client.get("/metrics")
        self.client.get("/")

    @task(1)
    def batch_operation(self):
        """Simulate batch operations with validation."""
        data = {
            "operations": [
                {
                    "type": "test",
                    "data": {
                        "value": random.randint(1, 100),
                        "timestamp": "2024-03-20T12:00:00Z"
                    }
                }
                for _ in range(random.randint(1, 5))
            ]
        }

        with self.client.post(
            "/batch",
            json=data,
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Batch operation failed: {response.status_code}")
            else:
                result = response.json()
                if result.get("operations") != len(data["operations"]):
                    response.failure("Operation count mismatch")

class LoadTest(BaseUser):
    """Simulates high load on the API."""
    wait_time = between(0.1, 0.5)  # Very short wait time for high load

    @task(5)
    def health_check(self):
        """Frequently check health endpoints."""
        self.client.get("/health")
        self.client.get("/ready")

    @task(3)
    def metrics(self):
        """Frequently check metrics."""
        self.client.get("/metrics")

    @task(2)
    def batch_operations(self):
        """Simulate frequent batch operations."""
        data = {
            "operations": [
                {
                    "type": "test",
                    "data": {
                        "value": random.randint(1, 100),
                        "timestamp": "2024-03-20T12:00:00Z"
                    }
                }
                for _ in range(random.randint(1, 3))
            ]
        }
        self.client.post("/batch", json=data)

class WorkflowUser(BaseUser):
    """Simulates complete user workflows."""
    wait_time = between(2, 5)

    @task
    def complete_workflow(self):
        """Simulate a complete user workflow."""
        # 1. Check system health
        self.client.get("/health")

        # 2. Perform batch operations
        data = {
            "operations": [
                {
                    "type": "workflow",
                    "data": {
                        "step": i,
                        "value": random.randint(1, 100)
                    }
                }
                for i in range(3)
            ]
        }
        self.client.post("/batch", json=data)

        # 3. Check metrics
        self.client.get("/metrics")

        # 4. Final health check
        self.client.get("/health")

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize test environment."""
    print(f"Running tests against {HOSTS[ENV]}")
    if ENV == "production":
        print("WARNING: Running against production environment!")
