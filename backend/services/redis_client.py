import os
import logging
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

redis_client: Redis | None = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not url or not token:
            raise RuntimeError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
        redis_client = Redis.from_url(url, password=token, decode_responses=True)
        logger.info("Redis connection established")
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis connection closed")
