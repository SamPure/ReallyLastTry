import logging
import platform
import psutil
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app, Gauge
from pythonjsonlogger import jsonlogger
from app.core.tracing import setup_tracing
from app.config import settings
from app.utils.redis_utils import get_redis

# Setup tracing
setup_tracing()

app = FastAPI(title="Lead Follow-up Service")

# Structured JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logging.getLogger().handlers = [logHandler]
logging.getLogger().setLevel(logging.INFO)

# System metrics
memory_usage = Gauge("memory_usage_bytes", "Memory usage in bytes")
cpu_usage = Gauge("cpu_usage_percent", "CPU usage in percent")


@app.get("/health")
def health():
    """
    Liveness probe: if this returns 200 the container is up.
    """
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.get("/ready")
def readiness():
    """
    Readiness probe: checks Redis + Supabase.
    """
    try:
        # Redis ping
        r = get_redis()
        r.ping()
        # Supabase ping (fetch count of 1 row)
        settings.supabase_client.table("followup_logs").select("id").limit(1).execute()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"dependency failure: {e}")


@app.get("/")
def root():
    return {"status": "ok"}


# Prometheus metrics
app.mount("/metrics", make_asgi_app())
