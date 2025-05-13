import redis
from app.config import settings


def get_redis():
    return redis.Redis.from_url(
        settings.CELERY_BROKER_URL, decode_responses=True, ssl=settings.REDIS_TLS
    )
