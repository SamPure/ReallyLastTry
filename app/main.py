import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from typing import Optional, Dict
from app.core.tracing import setup_tracing
from app.core.logging import setup_logging

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

# Setup logging
setup_logging()

# Initialize FastAPI app with metadata
app = FastAPI(
    title="Lead Follow-up Service",
    description="""
    A FastAPI service for managing lead follow-ups and automation.

    ## Features

    * Health monitoring
    * Batch processing
    * Email notifications
    * SMS integration
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
    logging.info("Application startup complete")

@app.get("/health", tags=["health"])
async def health() -> Dict[str, str]:
    """
    Health check endpoint for Railway.

    Returns:
        Dict[str, str]: Status message indicating service health

    Raises:
        HTTPException: If the service is unhealthy
    """
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
    return {"status": "ready"}

@app.get("/", tags=["health"])
async def root() -> Dict[str, str]:
    """
    Root endpoint that also serves as a health check.

    Returns:
        Dict[str, str]: Status message indicating service health
    """
    return {"status": "ok"}

# Mount metrics endpoint
app.mount("/metrics", make_asgi_app())
