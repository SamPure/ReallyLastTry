import pytest
import asyncio
from datetime import datetime
from app.services.retry_logger import RetryLogger, with_retry_logging, retry_logger

@pytest.fixture
def logger():
    """Create a fresh RetryLogger instance for each test."""
    return RetryLogger()

@pytest.mark.asyncio
async def test_retry_logging(logger):
    """Test basic retry logging functionality."""
    # Simulate a function that fails twice then succeeds
    attempt = 0

    @with_retry_logging(max_retries=3, job_name="test_job")
    async def failing_function():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise ValueError("Simulated failure")
        return True

    # Should succeed on third attempt
    result = await failing_function()
    assert result is True
    assert attempt == 3

    # Check retry stats
    stats = logger.get_stats()
    assert stats["retry_counts"]["test_job"] == 2
    assert stats["failure_counts"] == {}
    assert "test_job" in stats["last_failures"]

@pytest.mark.asyncio
async def test_max_retries_exceeded(logger):
    """Test behavior when max retries are exceeded."""

    @with_retry_logging(max_retries=2, job_name="max_retries_test")
    async def always_failing():
        raise ValueError("Always fails")

    # Should raise after max retries
    with pytest.raises(ValueError):
        await always_failing()

    # Check failure stats
    stats = logger.get_stats()
    assert stats["retry_counts"]["max_retries_test"] == 2
    assert stats["failure_counts"]["max_retries_test"] == 1
    assert "max_retries_test" in stats["last_failures"]

@pytest.mark.asyncio
async def test_retry_logger_metrics(logger):
    """Test retry logger metrics collection."""

    @with_retry_logging(max_retries=3, job_name="metrics_test")
    async def metrics_test():
        raise ValueError("Test error")

    # Run multiple times to test metrics accumulation
    for _ in range(3):
        with pytest.raises(ValueError):
            await metrics_test()

    stats = logger.get_stats()
    assert stats["retry_counts"]["metrics_test"] == 9  # 3 runs * 3 retries
    assert stats["failure_counts"]["metrics_test"] == 3  # 3 runs
    assert len(stats["last_failures"]) == 1

@pytest.mark.asyncio
async def test_multiple_jobs(logger):
    """Test tracking multiple different jobs."""

    @with_retry_logging(max_retries=2, job_name="job1")
    async def job1():
        raise ValueError("Job 1 error")

    @with_retry_logging(max_retries=2, job_name="job2")
    async def job2():
        raise ValueError("Job 2 error")

    # Run both jobs
    with pytest.raises(ValueError):
        await job1()
    with pytest.raises(ValueError):
        await job2()

    # Check stats for both jobs
    stats = logger.get_stats()
    assert "job1" in stats["retry_counts"]
    assert "job2" in stats["retry_counts"]
    assert stats["retry_counts"]["job1"] == 2
    assert stats["retry_counts"]["job2"] == 2
    assert len(stats["last_failures"]) == 2

@pytest.mark.asyncio
async def test_retry_logger_persistence(logger):
    """Test that retry logger maintains state between calls."""

    @with_retry_logging(max_retries=2, job_name="persistence_test")
    async def persistent_job():
        raise ValueError("Persistent error")

    # First run
    with pytest.raises(ValueError):
        await persistent_job()

    # Second run
    with pytest.raises(ValueError):
        await persistent_job()

    # Check accumulated stats
    stats = logger.get_stats()
    assert stats["retry_counts"]["persistence_test"] == 4  # 2 runs * 2 retries
    assert stats["failure_counts"]["persistence_test"] == 2  # 2 runs
    assert "persistence_test" in stats["last_failures"]

@pytest.mark.asyncio
async def test_retry_logger_error_types(logger):
    """Test handling of different error types."""

    @with_retry_logging(max_retries=2, job_name="error_types")
    async def raise_different_errors():
        if not hasattr(raise_different_errors, 'attempt'):
            raise_different_errors.attempt = 0
        raise_different_errors.attempt += 1

        if raise_different_errors.attempt == 1:
            raise ValueError("Value error")
        elif raise_different_errors.attempt == 2:
            raise RuntimeError("Runtime error")
        else:
            raise TypeError("Type error")

    # Should fail with TypeError after retries
    with pytest.raises(TypeError):
        await raise_different_errors()

    # Check error tracking
    stats = logger.get_stats()
    assert stats["retry_counts"]["error_types"] == 2
    assert stats["failure_counts"]["error_types"] == 1
    assert "error_types" in stats["last_failures"]
    assert "TypeError" in stats["last_failures"]["error_types"]["error_type"]
