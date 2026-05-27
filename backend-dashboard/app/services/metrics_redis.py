import logging
import os
import redis.asyncio as redis

logger = logging.getLogger("uvicorn.error")
REDIS_URL = os.getenv("REDIS_URL", "redis://dashboard-redis:6380")
BULK_KEY = "reproducciones:bulk"
MAX_BULK_EVENTS = 100_000
LOCK_KEY = "reproducciones:bulk:lock"
LOCK_TTL = 600  # 10 min, el doble del intervalo del worker
PAGE_SIZE = 500
DEAD_LETTER_KEY = "reproducciones:bulk:dead_letters"

_redis_client: redis.Redis | None = None


async def get_metrics_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            logger.warning("metrics_redis_connection_failed")
            _redis_client = None
    return _redis_client
