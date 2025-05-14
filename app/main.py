import logging
import sys
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional, Dict
import json
from datetime import datetime
from app.api import leads, messaging
from app.services.config_manager import get_settings
from app.core.logging import setup_logging
from app.services.supabase_client import supabase_client
from app.jobs.sheet_sync import sheet_sync
from fastapi.responses import JSONResponse
from app.jobs.email_scheduler import start_email_scheduler, stop_email_scheduler
from app.services.email_service import email_service, EmailService
from app.services.kixie_handler import KixieHandler
from app.services.google_sheets import GoogleSheetsService
from app.jobs.scheduler_service import SchedulerService
import time

# Initialize settings
settings = get_settings()

# Set up logging first
logger = logging.getLogger(__name__)

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
    title="Lead Management API",
    description="API for managing leads, communications, and analytics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Initialize services
email_service = EmailService()
kixie_handler = KixieHandler()
sheets_service = GoogleSheetsService()
scheduler_service = SchedulerService()

# Include routers
app.include_router(leads.router)
app.include_router(messaging.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize Supabase client
        await supabase_client.initialize()
        logger.info("Supabase client initialized")

        # Initialize Google Sheets sync
        await sheet_sync.initialize()
        logger.info("Google Sheets sync initialized")

        # Start email scheduler
        start_email_scheduler()
        logger.info("Application startup complete")

        # Initialize scheduler
        await scheduler_service.initialize()
        logger.info("Scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        # Close Kixie handler
        await kixie_handler.close()
        logger.info("Kixie handler closed")

        # Stop email scheduler
        stop_email_scheduler()
        logger.info("Application shutdown complete")

        # Cleanup scheduler
        await scheduler_service.cleanup()
        logger.info("Scheduler cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Supabase connection
        supabase_status = "healthy" if await supabase_client.is_connected() else "unhealthy"

        # Check email service
        email_status = "healthy" if email_service.is_healthy() else "unhealthy"

        # Check Google Sheets sync
        sheets_status = "healthy" if sheet_sync.is_healthy() else "unhealthy"

        return {
            "status": "healthy" if all(s == "healthy" for s in [supabase_status, email_status, sheets_status]) else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "supabase": supabase_status,
                "email_service": email_status,
                "sheets_sync": sheets_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes/container orchestration."""
    try:
        # Check if all critical services are ready
        is_ready = all([
            await supabase_client.is_connected(),
            email_service.is_healthy(),
            sheet_sync.is_healthy()
        ])

        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
