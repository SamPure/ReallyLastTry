import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class RetryLogger:
    """Service for logging retries and failures of async jobs."""

    def __init__(self):
        self.retry_counts: Dict[str, int] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_failures: Dict[str, Dict[str, Any]] = {}

    def log_retry(self, job_name: str, error: Exception, attempt: int, max_retries: int) -> None:
        """Log a retry attempt for a job."""
        self.retry_counts[job_name] = self.retry_counts.get(job_name, 0) + 1

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "job": job_name,
            "attempt": attempt,
            "max_retries": max_retries,
            "error": str(error),
            "error_type": type(error).__name__,
            "total_retries": self.retry_counts[job_name]
        }

        logger.warning(f"Job retry: {json.dumps(log_data)}")

    def log_failure(self, job_name: str, error: Exception, final_attempt: int) -> None:
        """Log a final failure after all retries."""
        self.failure_counts[job_name] = self.failure_counts.get(job_name, 0) + 1

        failure_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "job": job_name,
            "final_attempt": final_attempt,
            "error": str(error),
            "error_type": type(error).__name__,
            "total_failures": self.failure_counts[job_name]
        }

        self.last_failures[job_name] = failure_data
        logger.error(f"Job failed: {json.dumps(failure_data)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current retry and failure statistics."""
        return {
            "retry_counts": self.retry_counts,
            "failure_counts": self.failure_counts,
            "last_failures": self.last_failures
        }

# Global instance
retry_logger = RetryLogger()

def with_retry_logging(max_retries: int = 3, job_name: Optional[str] = None):
    """Decorator to add retry logging to async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal job_name
            if job_name is None:
                job_name = func.__name__

            attempt = 0
            last_error = None

            while attempt < max_retries:
                try:
                    attempt += 1
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        retry_logger.log_retry(job_name, e, attempt, max_retries)
                    else:
                        retry_logger.log_failure(job_name, e, attempt)
                        raise

            # This should never be reached due to the raise in the else clause
            raise last_error

        return wrapper
    return decorator

# Example usage:
# @with_retry_logging(max_retries=3, job_name="send_email")
# async def send_email(to: str, subject: str, body: str) -> bool:
#     # Email sending logic here
#     pass
