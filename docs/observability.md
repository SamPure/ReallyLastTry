# Observability Stack

This document describes the observability stack used in the application, including setup instructions and usage guidelines.

## Components

The observability stack consists of three main components:

1. **Jaeger** - Distributed tracing
2. **Prometheus** - Metrics collection
3. **Grafana** - Metrics visualization and dashboards

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Required Python packages (see `requirements.txt`)

### Starting the Stack

1. Start the observability stack:

   ```bash
   ./scripts/start_observability.sh
   ```

2. Access the UIs:
   - Jaeger: http://localhost:16686
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

### Stopping the Stack

```bash
docker-compose -f docker-compose.observability.yml down
```

## Metrics

The application exposes the following metrics:

### HTTP Metrics

- `http_requests_total` - Total number of HTTP requests
- `http_request_duration_seconds` - HTTP request duration
- `http_errors_total` - Total number of HTTP errors

### Batch Processing Metrics

- `batch_operations_total` - Total number of batch operations
- `batch_operation_duration_seconds` - Batch operation duration
- `batch_errors_total` - Total number of batch errors

### External Service Metrics

- `external_api_calls_total` - Total number of external API calls
- `external_api_duration_seconds` - External API call duration
- `external_api_errors_total` - Total number of external API errors

### Redis Metrics

- `redis_operations_total` - Total number of Redis operations
- `redis_operation_duration_seconds` - Redis operation duration
- `redis_errors_total` - Total number of Redis errors

### Celery Metrics

- `celery_tasks_total` - Total number of Celery tasks
- `celery_task_duration_seconds` - Celery task duration
- `celery_errors_total` - Total number of Celery errors

### System Metrics

- `memory_usage_bytes` - Memory usage in bytes
- `cpu_usage_percent` - CPU usage percentage

## Tracing

The application uses OpenTelemetry for distributed tracing. Key operations are traced using the `@trace_operation` decorator:

```python
from app.core.telemetry import trace_operation

@trace_operation("operation_name")
async def your_function():
    # Your code here
    pass
```

## Dashboards

The application includes a pre-configured Grafana dashboard with the following panels:

1. HTTP Request Rate
2. HTTP Request Duration
3. Error Rate
4. Memory Usage

### Adding Custom Dashboards

1. Create a new dashboard JSON file in `grafana/dashboards/`
2. Add the dashboard to `grafana/provisioning/dashboards/fastapi.yml`
3. Restart the Grafana container

## Troubleshooting

### Common Issues

1. **Metrics not showing up in Grafana**

   - Check Prometheus targets at http://localhost:9090/targets
   - Verify the FastAPI application is running and exposing metrics
   - Check network connectivity between services

2. **Traces not appearing in Jaeger**

   - Verify OpenTelemetry configuration in `app/core/telemetry.py`
   - Check Jaeger collector logs
   - Ensure the application is properly instrumented

3. **High resource usage**
   - Adjust scrape intervals in `prometheus.yml`
   - Reduce retention period for metrics
   - Optimize query patterns in Grafana dashboards

## Best Practices

1. **Metrics**

   - Use meaningful metric names
   - Include units in metric names
   - Add helpful descriptions
   - Use appropriate metric types (counter, gauge, histogram)

2. **Tracing**

   - Keep span names concise but descriptive
   - Add relevant attributes to spans
   - Use appropriate sampling rates
   - Correlate traces with logs

3. **Dashboards**
   - Keep dashboards focused and organized
   - Use appropriate visualization types
   - Set reasonable refresh intervals
   - Add helpful annotations

## Security Considerations

1. **Access Control**

   - Grafana admin password is set in `docker-compose.observability.yml`
   - Consider using environment variables for sensitive values
   - Restrict access to observability endpoints in production

2. **Data Retention**
   - Configure appropriate retention periods
   - Regularly clean up old data
   - Monitor storage usage

## Future Improvements

1. **Additional Metrics**

   - Business-specific metrics
   - User behavior metrics
   - Resource utilization metrics

2. **Enhanced Tracing**

   - More detailed operation tracing
   - Better error tracking
   - Performance bottleneck identification

3. **Advanced Dashboards**
   - Custom alerts
   - SLA monitoring
   - Trend analysis
