import logging
import sys
import uuid
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from opentelemetry import trace

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes trace context."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add request ID if available
        if not log_record.get('request_id'):
            log_record['request_id'] = str(uuid.uuid4())

        # Add trace context if available
        current_span = trace.get_current_span()
        if current_span.is_recording():
            context = current_span.get_span_context()
            log_record['trace_id'] = format(context.trace_id, '032x')
            log_record['span_id'] = format(context.span_id, '016x')

        # Add standard fields
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

def setup_logging(level: str = "INFO") -> None:
    """Configure logging with JSON formatting and trace context."""
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure JSON logging
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        '%(asctime)s %(level)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Set up root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Configure third-party loggers
    logging.getLogger("uvicorn").handlers = [handler]
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("fastapi").handlers = [handler]

    # Set log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    # Log startup message
    logging.info("Logging configured", extra={
        "log_level": level,
        "format": "json",
        "tracing": "enabled"
    })
