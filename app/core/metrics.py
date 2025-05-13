from opentelemetry.metrics import get_meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
import psutil

# Initialize meter
meter = get_meter(__name__)

# HTTP Metrics
http_requests_total = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1"
)

http_request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration in seconds",
    unit="s"
)

http_errors_total = meter.create_counter(
    name="http_errors_total",
    description="Total number of HTTP errors",
    unit="1"
)

# Batch Processing Metrics
batch_operations_total = meter.create_counter(
    name="batch_operations_total",
    description="Total number of batch operations processed",
    unit="1"
)

batch_operation_duration = meter.create_histogram(
    name="batch_operation_duration_seconds",
    description="Batch operation duration in seconds",
    unit="s"
)

batch_errors_total = meter.create_counter(
    name="batch_errors_total",
    description="Total number of batch processing errors",
    unit="1"
)

# External Service Metrics
external_api_calls_total = meter.create_counter(
    name="external_api_calls_total",
    description="Total number of external API calls",
    unit="1"
)

external_api_duration = meter.create_histogram(
    name="external_api_duration_seconds",
    description="External API call duration in seconds",
    unit="s"
)

external_api_errors_total = meter.create_counter(
    name="external_api_errors_total",
    description="Total number of external API errors",
    unit="1"
)

# Redis Metrics
redis_operations_total = meter.create_counter(
    name="redis_operations_total",
    description="Total number of Redis operations",
    unit="1"
)

redis_operation_duration = meter.create_histogram(
    name="redis_operation_duration_seconds",
    description="Redis operation duration in seconds",
    unit="s"
)

redis_errors_total = meter.create_counter(
    name="redis_errors_total",
    description="Total number of Redis errors",
    unit="1"
)

# Celery Metrics
celery_tasks_total = meter.create_counter(
    name="celery_tasks_total",
    description="Total number of Celery tasks processed",
    unit="1"
)

celery_task_duration = meter.create_histogram(
    name="celery_task_duration_seconds",
    description="Celery task duration in seconds",
    unit="s"
)

celery_errors_total = meter.create_counter(
    name="celery_errors_total",
    description="Total number of Celery task errors",
    unit="1"
)

# System Metrics
memory_usage_bytes = meter.create_observable_gauge(
    name="memory_usage_bytes",
    description="Memory usage in bytes",
    unit="bytes",
    callbacks=[lambda: [psutil.Process().memory_info().rss]]
)

cpu_usage_percent = meter.create_observable_gauge(
    name="cpu_usage_percent",
    description="CPU usage percentage",
    unit="percent",
    callbacks=[lambda: [psutil.Process().cpu_percent()]]
)
