from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class DeviceStateStore:
    def __init__(self, redis: Redis, heartbeat_ttl: int = 300, max_retries: int = 3):
        self.redis = redis
        self.heartbeat_ttl = heartbeat_ttl
        self.max_retries = max_retries

    @classmethod
    async def create(cls) -> "DeviceStateStore":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        heartbeat_ttl = int(os.getenv("DEVICE_HEARTBEAT_TTL", "300"))
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, heartbeat_ttl=heartbeat_ttl)

    async def close(self) -> None:
        await self.redis.close()

    async def _retry_operation(self, operation, *args, operation_name: str = "operation"):
        """Ejecuta una operación con reintentos exponenciales."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return await operation(*args)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = 0.5 * (attempt + 1)
                    logger.warning(f"[Redis] {operation_name} falló (intento {attempt + 1}/{self.max_retries}): {e}. Reintentando en {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[Redis] {operation_name} falló después de {self.max_retries} intentos: {e}")
        raise last_exception

    async def upsert_heartbeat(self, device_id: str, server_id: str | None = None) -> None:
        async def _do_upsert():
            now_epoch = int(time.time())
            now_iso = datetime.now(timezone.utc).isoformat()
            key = f"device:state:{device_id}"

            pipe = self.redis.pipeline()
            pipe.sadd("devices:all", device_id)
            pipe.hset(
                key,
                mapping={
                    "device_id": device_id,
                    "server_id": server_id or "",
                    "last_seen": now_iso,
                    "last_seen_epoch": str(now_epoch),
                    "online": "1",
                },
            )
            await pipe.execute()
        
        return await self._retry_operation(_do_upsert, operation_name=f"upsert_heartbeat({device_id})")

    async def mark_offline(self, device_id: str) -> None:
        async def _do_mark_offline():
            key = f"device:state:{device_id}"
            if await self.redis.exists(key):
                await self.redis.hset(key, mapping={"online": "0"})
        
        try:
            await self._retry_operation(_do_mark_offline, operation_name=f"mark_offline({device_id})")
        except Exception as e:
            logger.error(f"[Redis] mark_offline({device_id}) falló definitivamente: {e}")

    async def get_all_status(self) -> dict[str, dict[str, Any]]:
        async def _do_get_all():
            device_ids = await self.redis.smembers("devices:all")
            if not device_ids:
                return {}

            now_epoch = int(time.time())
            pipe = self.redis.pipeline()
            for device_id in device_ids:
                pipe.hgetall(f"device:state:{device_id}")
            rows = await pipe.execute()

            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                if not row:
                    continue

                device_id = row.get("device_id")
                if not device_id:
                    continue

                last_seen_epoch = int(row.get("last_seen_epoch", "0"))
                is_online_by_ttl = (now_epoch - last_seen_epoch) <= self.heartbeat_ttl
                explicit_online = str(row.get("online", "1")) == "1"

                result[device_id] = {
                    "online": bool(is_online_by_ttl and explicit_online),
                    "last_seen": row.get("last_seen"),
                    "server_id": row.get("server_id") or None,
                }

            return result
        
        try:
            return await self._retry_operation(_do_get_all, operation_name="get_all_status")
        except Exception as e:
            logger.error(f"[Redis] get_all_status falló definitivamente: {e}")
            return {}

    async def update_playing_content(self, device_id: str, content: dict | None) -> None:
        async def _do_update():
            key = f"device:playing:{device_id}"
            if content is None:
                await self.redis.delete(key)
            else:
                import json
                await self.redis.set(key, json.dumps(content), ex=self.heartbeat_ttl)
        
        try:
            await self._retry_operation(_do_update, operation_name=f"update_playing_content({device_id})")
        except Exception as e:
            logger.error(f"[Redis] update_playing_content({device_id}) falló: {e}")

    async def get_playing_content(self, device_id: str) -> dict | None:
        async def _do_get():
            key = f"device:playing:{device_id}"
            data = await self.redis.get(key)
            if data:
                import json
                return json.loads(data)
            return None
        
        try:
            return await self._retry_operation(_do_get, operation_name=f"get_playing_content({device_id})")
        except Exception as e:
            logger.error(f"[Redis] get_playing_content({device_id}) falló: {e}")
            return None

    async def remove_device(self, device_id: str) -> None:
        """Elimina completamente un dispositivo de Redis (state, playing, y del set devices:all)."""
        async def _do_remove():
            keys_to_delete = [
                f"device:state:{device_id}",
                f"device:playing:{device_id}",
            ]
            for key in keys_to_delete:
                await self.redis.delete(key)
            await self.redis.srem("devices:all", device_id)

        try:
            await self._retry_operation(_do_remove, operation_name=f"remove_device({device_id})")
        except Exception as e:
            logger.error(f"[Redis] remove_device({device_id}) falló definitivamente: {e}")
