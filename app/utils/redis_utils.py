import os
from typing import Optional
from redis import Redis
from redis.connection import ConnectionPool

def get_redis_client(
    url: Optional[str] = None,
    use_ssl: bool = True
) -> Redis:
    """
    Create a Redis client from a URL.
    If no URL is provided, uses CELERY_BROKER_URL from environment.
    """
    if url is None:
        url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    pool = ConnectionPool.from_url(
        url,
        ssl=use_ssl,
        ssl_cert_reqs=None if use_ssl else None
    )

    return Redis(connection_pool=pool)
