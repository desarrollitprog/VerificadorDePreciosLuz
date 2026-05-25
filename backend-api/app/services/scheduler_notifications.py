from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class SchedulerNotifications:
    def __init__(self, redis: Redis, default_ttl: int = 86400):
        self.redis = redis
        self.default_ttl = default_ttl
        self.key_prefix = "pending:scheduler"

    @classmethod
    async def create(cls, ttl_seconds: int = 86400) -> "SchedulerNotifications":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, default_ttl=ttl_seconds)

    async def close(self) -> None:
        await self.redis.close()

    def _make_key(self, banner_id: int, command: str) -> str:
        return f"{self.key_prefix}:{banner_id}_{command}"

    async def save_pending_notification(
        self,
        banner_id: int,
        device_ids: str | None,
        titulo: str | None,
        url: str,
        tipo: str,
        fecha_inicio: datetime | None,
        fecha_fin: datetime | None,
        command: str,
        scheduled_at: datetime | None = None,
    ) -> bool:
        key = self._make_key(banner_id, command)

        fecha_inicio_iso = fecha_inicio.isoformat() if fecha_inicio else None
        fecha_fin_iso = fecha_fin.isoformat() if fecha_fin else None
        scheduled_at_iso = scheduled_at.isoformat() if scheduled_at else datetime.now(timezone(timedelta(hours=-4))).isoformat()

        data = {
            "banner_id": banner_id,
            "titulo": titulo or "",
            "url": url,
            "tipo": tipo,
            "device_ids": device_ids or "",
            "fecha_inicio": fecha_inicio_iso,
            "fecha_fin": fecha_fin_iso,
            "command": command,
            "scheduled_at": scheduled_at_iso,
        }

        try:
            await self.redis.set(key, json.dumps(data), ex=self.default_ttl)
            logger.info(f"[Scheduler] Notificación pendiente guardada: banner={banner_id}, command={command}")
            return True
        except Exception as e:
            logger.error(f"[Scheduler] Error guardando notificación pendiente: {e}")
            return False

    async def get_pending_notification(self, banner_id: int, command: str) -> dict[str, Any] | None:
        key = self._make_key(banner_id, command)
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[Scheduler] Error obteniendo notificación pendiente: {e}")
            return None

    async def get_all_pending_notifications(self) -> list[dict[str, Any]]:
        try:
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            results = []
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    try:
                        results.append(json.loads(data))
                    except Exception:
                        pass
            return results
        except Exception as e:
            logger.error(f"[Scheduler] Error obteniendo todas las notificaciones pendientes: {e}")
            return []

    async def remove_pending_notification(self, banner_id: int, command: str) -> bool:
        key = self._make_key(banner_id, command)
        try:
            deleted = await self.redis.delete(key)
            if deleted:
                logger.info(f"[Scheduler] Notificación pendiente eliminada: banner={banner_id}, command={command}")
            return bool(deleted)
        except Exception as e:
            logger.error(f"[Scheduler] Error eliminando notificación pendiente: {e}")
            return False


scheduler_notifications: SchedulerNotifications | None = None


async def save_pending_notification(
    banner_id: int,
    device_ids: str | None,
    titulo: str | None,
    url: str,
    tipo: str,
    fecha_inicio: datetime | None,
    fecha_fin: datetime | None,
    command: str,
    scheduled_at: datetime | None = None,
) -> bool:
    if scheduler_notifications is None:
        logger.warning("[Scheduler] scheduler_notifications no inicializado")
        return False
    return await scheduler_notifications.save_pending_notification(
        banner_id=banner_id,
        device_ids=device_ids,
        titulo=titulo,
        url=url,
        tipo=tipo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        command=command,
        scheduled_at=scheduled_at,
    )


async def get_pending_notification(banner_id: int, command: str) -> dict[str, Any] | None:
    if scheduler_notifications is None:
        return None
    return await scheduler_notifications.get_pending_notification(banner_id, command)


async def get_all_pending_notifications() -> list[dict[str, Any]]:
    if scheduler_notifications is None:
        return []
    return await scheduler_notifications.get_all_pending_notifications()


async def remove_pending_notification(banner_id: int, command: str) -> bool:
    if scheduler_notifications is None:
        return False
    return await scheduler_notifications.remove_pending_notification(banner_id, command)
