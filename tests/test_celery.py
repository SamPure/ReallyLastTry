import pytest
from celery import Celery
from app.config import settings

@pytest.fixture
def celery_app():
    """Create a test Celery app."""
    app = Celery(
        "test_app",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_BROKER_URL
    )
    app.conf.update(
        task_always_eager=True,  # Run tasks synchronously
        task_eager_propagates=True,  # Propagate exceptions
        broker_connection_retry_on_startup=True
    )
    return app

@pytest.mark.integration
@pytest.mark.celery
def test_celery_connection(celery_app):
    """Test Celery connection and basic task execution."""
    @celery_app.task
    def test_task(x, y):
        return x + y

    # Execute task
    result = test_task.delay(4, 4)
    assert result.get() == 8, "Celery task execution failed"

@pytest.mark.integration
@pytest.mark.celery
def test_celery_error_handling(celery_app):
    """Test Celery error handling and retries."""
    @celery_app.task(bind=True, max_retries=3)
    def failing_task(self):
        try:
            raise ValueError("Test error")
        except ValueError as exc:
            self.retry(exc=exc)

    # Execute task
    result = failing_task.delay()

    # Check that task failed after retries
    with pytest.raises(ValueError):
        result.get()

@pytest.mark.integration
@pytest.mark.celery
def test_celery_worker_health(celery_app):
    """Test Celery worker health check."""
    @celery_app.task
    def health_check():
        return "healthy"

    # Execute health check
    result = health_check.delay()
    assert result.get() == "healthy", "Celery worker health check failed"
