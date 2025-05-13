import logging
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from pythonjsonlogger import jsonlogger

# Structured JSON logging
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

app = FastAPI(title="Lead Follow-up Service")


@app.get("/health")
def health():
    # Railway liveness probe
    return {"status": "ok"}


@app.get("/")
def root():
    # Railway root probe
    return {"status": "ok"}


# (Optional) Prometheus metrics
app.mount("/metrics", make_asgi_app())
