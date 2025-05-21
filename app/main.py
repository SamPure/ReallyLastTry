import logging
import sys
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional, Dict
import json
from datetime import datetime
from app.api import leads, messaging
from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.jobs.sheet_sync import sheet_sync
from fastapi.responses import JSONResponse
from app.jobs.email_scheduler import start_email_scheduler, stop_email_scheduler
from app.services.email_service import email_service, EmailService
from app.services.kixie_handler import KixieHandler
from app.services.google_sheets import GoogleSheetsService
from app.jobs.scheduler_service import start_scheduler, is_healthy as scheduler_healthy
from app.services.retry_logger import retry_logger
from app.jobs.followup_service import followup_service
from app.services.prometheus_metrics import collect_metrics
import time

# Initialize settings
settings = get_settings()

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

# Set up logging globally
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Get module logger
logger = logging.getLogger(__name__)

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

# Include routers
app.include_router(leads.router)
app.include_router(messaging.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize Supabase client
        try:
            get_supabase_client().initialize()
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.exception("Failed to initialize Supabase client: %s", e)
            raise

        # Start email scheduler
        try:
            start_email_scheduler()
            logger.info("Email scheduler started")
        except Exception as e:
            logger.exception("Failed to start email scheduler: %s", e)
            raise

        # Start follow-up scheduler
        try:
            start_scheduler()
            logger.info("Follow-up scheduler started")
        except Exception as e:
            logger.exception("Failed to start follow-up scheduler: %s", e)
            raise

        logger.info("Application startup complete")
    except Exception as e:
        logger.exception("Startup failed: %s", e)
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
        logger.info("Email scheduler stopped")

        # Stop follow-up scheduler
        if followup_service.scheduler.running:
            followup_service.scheduler.shutdown()
            logger.info("Follow-up scheduler stopped")

        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        email_health = email_service.is_healthy()
        scheduler_health = scheduler_healthy()

        if not (email_health and scheduler_health):
            raise HTTPException(status_code=503, detail="Service unhealthy")

        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check if services are initialized
        if not email_service.gmail_service:
            logger.warning("Gmail service not initialized")
            raise HTTPException(status_code=503, detail="Gmail service not initialized")

        # Check if Supabase is connected
        if not await get_supabase_client().is_connected():
            logger.warning("Supabase not connected")
            raise HTTPException(status_code=503, detail="Supabase not connected")

        # Check if scheduler is running
        if not scheduler_healthy():
            logger.warning("Scheduler not healthy")
            raise HTTPException(status_code=503, detail="Scheduler not healthy")

        return {
            "status": "ready",
            "services": {
                "email": "initialized",
                "supabase": "connected",
                "scheduler": "running"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        # Collect and update metrics
        collect_metrics()

        # Return metrics in Prometheus format
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        reload=True
    )
