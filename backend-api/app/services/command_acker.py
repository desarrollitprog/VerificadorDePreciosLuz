from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CommandAcker:
    """Maneja confirmaciones de comandos via Redis.
    
    Permite que cualquier worker procese confirmaciones de comandos,
    eliminando el problema de múltiples workers con dictionaries locales.
    TTL de 120s: suficientemente largo para polling (60s), lo suficientemente
    corto para que acks de comandos anteriores no interfieran.
    """

    def __init__(self, redis: Redis, ttl: int = 120):
        self.redis = redis
        self.ttl = ttl

    @classmethod
    async def create(cls, ttl: int = 120) -> "CommandAcker":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, ttl=ttl)

    async def close(self) -> None:
        await self.redis.close()

    async def save_confirmation(
        self, 
        device_id: str, 
        command: str, 
        status: str, 
        reason: str = "",
        command_id: str | None = None,
    ) -> None:
        """Guarda una confirmación en Redis con TTL."""
        key = f"command:ack:{device_id}:{command}"
        data = json.dumps({
            "device_id": device_id,
            "command": command,
            "status": status,
            "reason": reason,
            "command_id": command_id,
            "timestamp": time.time()
        })
        await self.redis.set(key, data, ex=self.ttl)
        logger.info(f"[ACKER] Confirmación guardada en Redis: key={key}, status={status}")

    async def get_confirmation(self, device_id: str, command: str) -> dict[str, Any] | None:
        """Obtiene una confirmación de Redis."""
        key = f"command:ack:{device_id}:{command}"
        data = await self.redis.get(key)
        if data:
            logger.info(f"[ACKER] Confirmación encontrada en Redis: key={key}")
            return json.loads(data)
        logger.debug(f"[ACKER] Sin confirmación en Redis: key={key}")
        return None

    async def delete_confirmation(self, device_id: str, command: str) -> None:
        """Elimina una confirmación de Redis."""
        key = f"command:ack:{device_id}:{command}"
        await self.redis.delete(key)
        logger.info(f"[ACKER] Confirmación eliminada de Redis: key={key}")

    async def get_all_pending(self) -> dict[str, dict[str, Any]]:
        """Obtiene todas las confirmaciones pendientes (para debugging)."""
        pattern = "command:ack:*"
        result = {}
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)
            if data:
                result[key] = json.loads(data)
        return result


command_acker: CommandAcker | None = None
