from prometheus_client import Counter, Gauge, Histogram, Summary
from typing import Dict, Any
from app.services.email_service import email_service
from app.services.retry_logger import retry_logger
from app.jobs.followup_service import followup_service

# Email Service Metrics
EMAILS_SENT = Counter(
    'emails_sent_total',
    'Total number of emails sent successfully',
    ['template']
)

EMAILS_FAILED = Counter(
    'emails_failed_total',
    'Total number of failed email attempts',
    ['error_type']
)

EMAIL_QUEUE_SIZE = Gauge(
    'email_queue_size',
    'Current size of the email queue'
)

EMAIL_RETRY_QUEUE_SIZE = Gauge(
    'email_retry_queue_size',
    'Current size of the email retry queue'
)

EMAIL_SEND_DURATION = Histogram(
    'email_send_duration_seconds',
    'Time spent sending emails',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Follow-up Service Metrics
FOLLOWUPS_SENT = Counter(
    'followups_sent_total',
    'Total number of follow-up emails sent',
    ['template']
)

FOLLOWUPS_FAILED = Counter(
    'followups_failed_total',
    'Total number of failed follow-up attempts',
    ['error_type']
)

FOLLOWUP_QUEUE_SIZE = Gauge(
    'followup_queue_size',
    'Current size of the follow-up queue'
)

# Retry Logger Metrics
RETRY_ATTEMPTS = Counter(
    'retry_attempts_total',
    'Total number of retry attempts',
    ['job_name']
)

RETRY_FAILURES = Counter(
    'retry_failures_total',
    'Total number of retry failures',
    ['job_name']
)

# Service Health Metrics
SERVICE_HEALTH = Gauge(
    'service_health',
    'Health status of services',
    ['service']
)

def collect_metrics() -> Dict[str, Any]:
    """Collect all metrics from services and update Prometheus metrics."""
    # Email Service Metrics
    email_stats = email_service.get_stats()
    email_metrics = email_service.metrics

    EMAIL_QUEUE_SIZE.set(len(email_service.email_queue))
    EMAIL_RETRY_QUEUE_SIZE.set(len(email_service.retry_queue))

    # Update counters based on metrics
    EMAILS_SENT.labels(template='default').inc(email_metrics.total_sent)
    EMAILS_FAILED.labels(error_type='default').inc(email_metrics.total_failed)

    # Service health
    SERVICE_HEALTH.labels(service='email').set(1 if email_service.is_healthy() else 0)

    # Follow-up Service Metrics
    followup_stats = followup_service.get_stats()

    FOLLOWUP_QUEUE_SIZE.set(followup_stats['queue_size'])
    FOLLOWUPS_SENT.labels(template='default').inc(followup_stats['metrics']['successful_followups'])
    FOLLOWUPS_FAILED.labels(error_type='default').inc(followup_stats['metrics']['failed_followups'])

    # Service health
    SERVICE_HEALTH.labels(service='followup').set(1 if followup_service.is_healthy() else 0)

    # Retry Logger Metrics
    retry_stats = retry_logger.get_stats()

    for job_name, count in retry_stats['retry_counts'].items():
        RETRY_ATTEMPTS.labels(job_name=job_name).inc(count)

    for job_name, count in retry_stats['failure_counts'].items():
        RETRY_FAILURES.labels(job_name=job_name).inc(count)

    return {
        'email_service': email_stats,
        'followup_service': followup_stats,
        'retry_logger': retry_stats
    }
