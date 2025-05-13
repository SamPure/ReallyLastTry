import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.metrics import get_meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_telemetry(app):
    """Set up OpenTelemetry instrumentation for the application."""
    try:
        # Create a resource with service information
        resource = Resource.create({
            "service.name": "fastapi-app",
            "service.version": "1.0.0",
            "deployment.environment": settings.ENVIRONMENT
        })

        # Set up Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )

        # Set up trace provider
        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        trace.set_tracer_provider(trace_provider)

        # Set up metric provider
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint="http://localhost:4317")
        )
        metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        meter = get_meter(__name__)

        # Create metrics
        request_counter = meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        request_duration = meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        error_counter = meter.create_counter(
            name="http_errors_total",
            description="Total number of HTTP errors",
            unit="1"
        )

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace_provider,
            meter_provider=metric_provider
        )

        # Instrument Redis
        RedisInstrumentor().instrument()

        # Instrument HTTP requests
        RequestsInstrumentor().instrument()

        logger.info("OpenTelemetry instrumentation set up successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to set up OpenTelemetry: {str(e)}")
        return False

def get_tracer(name: Optional[str] = None):
    """Get a tracer instance."""
    return trace.get_tracer(name or __name__)

def trace_operation(operation_name: str):
    """Decorator for tracing operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator
