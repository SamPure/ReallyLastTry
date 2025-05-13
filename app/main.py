import logging
import sys
from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from typing import Optional
from app.core.tracing import setup_tracing

try:
    from app.config import settings
except Exception as e:
    logging.warning(f"Could not load settings: {e}")
    settings: Optional[object] = None

# Setup tracing
try:
    setup_tracing()
except Exception as e:
    logging.warning(f"Tracing setup failed: {e}")

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

app = FastAPI(title="Lead Follow-up Service")

@app.on_event("startup")
async def startup_event():
    logging.info("Application startup complete")

@app.get("/health")
async def health():
    """
    Liveness probe for Railway.
    Returns 200 if the service is up and running.
    """
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    """Readiness: always healthy (no deps)"""
    return {"status": "ready"}

@app.get("/")
async def root():
    """
    Root endpoint that also serves as a health check.
    Returns 200 if the service is up and running.
    """
    return {"status": "ok"}

# Mount metrics endpoint
app.mount("/metrics", make_asgi_app())
