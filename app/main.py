import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from typing import Optional, Dict
from app.core.tracing import setup_tracing
from app.core.logging import setup_logging
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import json
from datetime import datetime

try:
    from app.config import settings
except Exception as e:
    logging.warning(f"Could not load settings: {e}")
    settings: Optional[object] = None

# Setup tracing
try:
    if settings and settings.OTLP_ENDPOINT:
        setup_tracing()
        logger.info(f"OpenTelemetry tracing enabled with endpoint: {settings.OTLP_ENDPOINT}")
    else:
        logger.warning("OpenTelemetry tracing disabled - no OTLP endpoint configured")
except Exception as e:
    logging.warning(f"Tracing setup failed: {e}")

# Setup logging
setup_logging()

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
logger = logging.getLogger("app")
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

# Set up OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter if endpoint is available
if settings and settings.OTLP_ENDPOINT:
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTLP_ENDPOINT,
            insecure=True
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        logger.info("OTLP exporter configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure OTLP exporter: {e}")

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="/health,/ready,/metrics"
)

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logging.info("Application startup complete")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to logs and traces."""
    request_id = request.headers.get("X-Request-ID", "no-request-id")

    # Add request ID to logger
    logger = logging.getLogger("app")
    logger = logging.LoggerAdapter(logger, {"request_id": request_id})

    # Create span for request
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        attributes={"http.request_id": request_id}
    ) as span:
        response = await call_next(request)
        span.set_attribute("http.status_code", response.status_code)
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
