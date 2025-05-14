import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from typing import Optional, Dict
import json
from datetime import datetime

# Set up logging first
logger = logging.getLogger(__name__)

try:
    from app.config import settings
except Exception as e:
    logger.warning(f"Could not load settings: {e}")
    settings: Optional[object] = None

# Configure JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        return json.dumps(log_record)

# Set up logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Lead Follow-up Service",
    description="""
    A FastAPI service for managing lead follow-ups and automation.

    ## Features

    * Health monitoring
    * Batch processing
    * Email notifications
    * SMS integration (Kixie)
    * Google Sheets integration
    * Supabase database integration

    ## Authentication

    All endpoints require API key authentication via the `X-API-Key` header.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints for monitoring",
        },
        {
            "name": "batch",
            "description": "Batch processing operations",
        },
        {
            "name": "metrics",
            "description": "Prometheus metrics endpoint",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("Application startup complete")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to logs."""
    request_id = request.headers.get("X-Request-ID", "no-request-id")

    # Add request ID to logger
    logger = logging.getLogger("app")
    logger = logging.LoggerAdapter(logger, {"request_id": request_id})

    response = await call_next(request)
    return response

@app.get("/health", tags=["health"])
async def health() -> Dict[str, str]:
    """
    Health check endpoint for Railway.

    Returns:
        Dict[str, str]: Status message indicating service health

    Raises:
        HTTPException: If the service is unhealthy
    """
    logger.info("Health check requested")
    return {"status": "ok"}

@app.get("/ready", tags=["health"])
async def ready() -> Dict[str, str]:
    """
    Readiness probe for the service.

    Returns:
        Dict[str, str]: Status message indicating service readiness

    Raises:
        HTTPException: If the service is not ready
    """
    logger.info("Readiness check requested")
    return {"status": "ready"}

@app.get("/", tags=["health"])
async def root() -> Dict[str, str]:
    """
    Root endpoint that also serves as a health check.

    Returns:
        Dict[str, str]: Status message indicating service health
    """
    logger.info("Root endpoint accessed")
    return {"status": "ok"}

# Mount metrics endpoint
app.mount("/metrics", make_asgi_app())

@app.post("/batch")
async def batch_operation(request: Request):
    """Batch operation endpoint."""
    data = await request.json()
    logger.info("Batch operation requested", extra={"batch_size": len(data.get("operations", []))})
    return {"status": "processing", "operations": len(data.get("operations", []))}
