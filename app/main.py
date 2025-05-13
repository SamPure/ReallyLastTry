import logging
from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app

# JSON logging
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

app = FastAPI(title="Lead Follow-up Service")


@app.get("/health")
def health():
    # Liveness probe for Railway
    return {"status": "ok"}


@app.get("/")
def root():
    # Root always returns 200
    return {"status": "ok"}

# (optional) Prometheus metrics
app.mount("/metrics", make_asgi_app())
