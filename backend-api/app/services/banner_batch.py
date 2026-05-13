from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Awaitable

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class BannerBatchManager:
    """Acumula banners que inician a la misma hora y los envía como un solo BANNER_LIST.

    Estructura en Redis:
        banner:batch:pending       → LIST - banners acumulados esperando broadcast
        banner:batch:coordinator   → String (SET NX, TTL 7s) - coordinador del lote

    El primer worker que acumula un banner se convierte en coordinador y
    programa un flush tras BATCH_WINDOW segundos. Todos los demás workers
    simplemente agregan sus banners a la lista. Al hacer flush, se lee y
    limpia la lista atómicamente y se envía un solo BANNER_LIST.
    """

    PENDING_KEY = "banner:batch:pending"
    COORD_KEY = "banner:batch:coordinator"
    BATCH_WINDOW = 5
    COORD_TTL = 7

    def __init__(self, redis: Redis):
        self.redis = redis

    @classmethod
    async def create(cls) -> "BannerBatchManager":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis)

    async def close(self) -> None:
        await self.redis.close()

    async def accumulate(self, banner_info: dict) -> bool:
        """Agrega un banner al lote pendiente.

        Retorna True si este worker es el coordinador (debe programar el flush).
        Retorna False si otro worker ya está coordinando.
        """
        await self.redis.rpush(self.PENDING_KEY, json.dumps(banner_info))
        logger.info(
            "[BANNER_BATCH] Banner %s acumulado en lote pendiente",
            banner_info.get("banner_id"),
        )

        is_coordinator = await self.redis.set(
            self.COORD_KEY, "1", nx=True, ex=self.COORD_TTL
        )
        return is_coordinator is not None

    async def flush(self, send_fn: Callable[[dict], Awaitable[None]]) -> list[dict]:
        """Lee y limpia la lista de pendientes, envía vía send_fn y retorna los banners."""
        pipe = self.redis.pipeline()
        pipe.lrange(self.PENDING_KEY, 0, -1)
        pipe.delete(self.PENDING_KEY)
        pipe.delete(self.COORD_KEY)
        results = await pipe.execute()

        raw_list: list[str] = results[0]
        if not raw_list:
            return []

        banners = []
        for raw in raw_list:
            try:
                banners.append(json.loads(raw))
            except json.JSONDecodeError as e:
                logger.warning("[BANNER_BATCH] Error decodificando banner: %s", e)

        if banners:
            message = {"command": "BANNER_LIST", "banners": banners}
            await send_fn(message)
            logger.info(
                "[BANNER_BATCH] BANNER_LIST enviado con %d banners",
                len(banners),
            )

        return banners


banner_batch_manager: BannerBatchManager | None = None
