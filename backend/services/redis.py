import logging

from upstash_redis.asyncio import Redis

from config.settings import settings

logger = logging(__name__)

_client: Redis | None = None


async def get_redis() -> Redis:
    global _client
    if _client is None:
        if not settings.upstash_redis_url:
            raise RuntimeError("UPSTASH_REDIS_REST_URL not set")
        _client = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)
        logger.info("Redis connection established")
    return _client


async def close_redis():
    global _client
    if _client:
        _client = None
        logger.info("Redis connection closed")
