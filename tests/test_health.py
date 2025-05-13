import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test the /health endpoint returns 200 OK with correct response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"

def test_ready_endpoint():
    """Test the /ready endpoint returns 200 OK with correct response."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert response.headers["content-type"] == "application/json"

def test_root_endpoint():
    """Test the root endpoint returns 200 OK with correct response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"

def test_metrics_endpoint():
    """Test the /metrics endpoint returns 200 OK with Prometheus metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_info" in response.text  # Basic Prometheus metric
    assert response.headers["content-type"] == "text/plain; version=0.0.4"
