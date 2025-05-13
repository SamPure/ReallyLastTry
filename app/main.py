import logging
from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from app.core.tracing import setup_tracing
from app.config import settings

# Setup tracing
setup_tracing()

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

@app.get("/")
async def root():
    """
    Root endpoint that also serves as a health check.
    Returns 200 if the service is up and running.
    """
    return {"status": "ok"}

# (optional) Prometheus metrics
app.mount("/metrics", make_asgi_app())
