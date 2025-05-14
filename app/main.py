import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from typing import Optional, Dict
import json
from datetime import datetime
from app.api import leads, messaging
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.supabase_client import supabase
from app.jobs.sheet_sync import sheet_sync
from fastapi.responses import JSONResponse
from app.services.config_manager import get_settings
from app.jobs.email_scheduler import start_email_scheduler, stop_email_scheduler

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

# Include routers
app.include_router(leads.router)
app.include_router(messaging.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize Supabase client
        await supabase.initialize()
        logger.info("Supabase client initialized")

        # Initialize Google Sheets sync
        await sheet_sync.initialize()
        logger.info("Google Sheets sync initialized")

        # Start email scheduler
        start_email_scheduler()
        logger.info("Application startup complete")
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
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
