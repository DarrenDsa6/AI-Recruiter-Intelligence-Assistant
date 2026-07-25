import logging

from config.constants import RATE_LIMIT_MAX_MESSAGES, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger(__name__)


async def check_rate_limit(redis, session_key: str) -> str | None:
    rate_key = f"chat_rate:{session_key}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
    if count > RATE_LIMIT_MAX_MESSAGES:
        return f"Rate limit exceeded. Max {RATE_LIMIT_MAX_MESSAGES} messages per hour."
    return None
