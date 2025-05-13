import pytest
import redis
from app.config import settings

@pytest.mark.integration
@pytest.mark.redis
def test_redis_connection():
    """Test Redis connection and basic operations."""
    # Create Redis client
    r = redis.Redis(
        host=settings.REDIS_URL.split("://")[1].split(":")[0],
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        ssl=settings.REDIS_SSL,
        db=settings.REDIS_DB
    )

    # Test connection
    assert r.ping(), "Redis connection failed"

    # Test basic operations
    test_key = "test:integration:key"
    test_value = "test_value"

    # Set value
    r.set(test_key, test_value)
    assert r.get(test_key).decode() == test_value, "Redis set/get failed"

    # Delete test key
    r.delete(test_key)
    assert not r.exists(test_key), "Redis delete failed"

@pytest.mark.integration
@pytest.mark.redis
def test_redis_error_handling():
    """Test Redis error handling and reconnection."""
    # Create Redis client with invalid password
    r = redis.Redis(
        host=settings.REDIS_URL.split("://")[1].split(":")[0],
        port=settings.REDIS_PORT,
        password="invalid_password",
        ssl=settings.REDIS_SSL,
        db=settings.REDIS_DB
    )

    # Test connection failure
    with pytest.raises(redis.AuthenticationError):
        r.ping()

@pytest.mark.integration
@pytest.mark.redis
def test_redis_pubsub():
    """Test Redis pub/sub functionality."""
    r = redis.Redis(
        host=settings.REDIS_URL.split("://")[1].split(":")[0],
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        ssl=settings.REDIS_SSL,
        db=settings.REDIS_DB
    )

    # Create pubsub instance
    pubsub = r.pubsub()

    # Subscribe to test channel
    test_channel = "test:integration:channel"
    pubsub.subscribe(test_channel)

    # Publish message
    test_message = "test_message"
    r.publish(test_channel, test_message)

    # Get message
    message = pubsub.get_message(timeout=1)
    assert message is not None, "No message received"
    assert message["type"] == "message", "Unexpected message type"
    assert message["data"].decode() == test_message, "Message content mismatch"

    # Unsubscribe
    pubsub.unsubscribe(test_channel)
