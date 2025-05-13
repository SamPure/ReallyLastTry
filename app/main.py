import logging
import platform
import psutil
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app, Gauge
from pythonjsonlogger import jsonlogger
from app.core.tracing import setup_tracing
from app.config import settings

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
memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage in percent')

@app.get("/health")
def health():
    try:
        # Check Redis connection
        redis = get_redis()
        redis.ping()

        # Check Supabase connection
        settings.supabase_client.table("followup_logs").select("count").limit(1).execute()

        # Update system metrics
        memory_usage.set(psutil.Process().memory_info().rss)
        cpu_usage.set(psutil.cpu_percent())

        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "system": {
                "python": platform.python_version(),
                "memory_usage": f"{psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB",
                "cpu_usage": f"{psutil.cpu_percent()}%"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# Prometheus metrics
app.mount("/metrics", make_asgi_app())
