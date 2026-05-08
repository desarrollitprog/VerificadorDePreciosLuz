from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class PendingCommandQueue:
    """Cola persistente de comandos en Redis con tracking de inflight.

    Estructura en Redis:
        device:queue:{device_id}             → LIST - comandos pendientes
        device:queue:{device_id}:inflight    → LIST - enviados, esperando confirmación
        device:queue:{device_id}:ttl         → TTL del dispositivo (se refresca en cleanup)

    Usa LMOVE atómico para mover de pendiente a inflight sin perder mensajes.
    """

    QUEUE_PREFIX = "device:queue"
    INFLIGHT_SUFFIX = "inflight"
    PENDING_SYNC_PREFIX = "device:pending:sync"
    PENDING_REBOOT_PREFIX = "device:pending:reboot"
    PENDING_BANNER_PREFIX = "device:pending:banner"
    MAX_QUEUE_PER_DEVICE = 100
    MAX_MESSAGE_AGE = 86400  # 24h

    def __init__(self, redis: Redis):
        self.redis = redis

    @classmethod
    async def create(cls) -> "PendingCommandQueue":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis)

    def _queue_key(self, device_id: str) -> str:
        return f"{self.QUEUE_PREFIX}:{device_id}"

    def _inflight_key(self, device_id: str) -> str:
        return f"{self.QUEUE_PREFIX}:{device_id}:{self.INFLIGHT_SUFFIX}"

    async def enqueue(self, device_id: str, message: dict) -> bool:
        """Encola un comando en Redis. Retorna True si se encoló, False si cola llena."""
        key = self._queue_key(device_id)
        inflight_key = self._inflight_key(device_id)

        # Verificar tamaño total (queue + inflight)
        queue_len = await self.redis.llen(key)
        inflight_len = await self.redis.llen(inflight_key)
        total = queue_len + inflight_len

        if total >= self.MAX_QUEUE_PER_DEVICE:
            logger.warning(
                f"[QUEUE] Cola llena para {device_id} "
                f"({total}/{self.MAX_QUEUE_PER_DEVICE} msgs), descartando mensaje"
            )
            return False

        message_with_ts = {**message, "enqueued_at": time.time()}
        await self.redis.rpush(key, json.dumps(message_with_ts))
        logger.info(
            f"[QUEUE] Mensaje encolado en Redis para {device_id} "
            f"(cola: {queue_len + 1}, inflight: {inflight_len})"
        )
        return True

    async def dequeue(self, device_id: str) -> dict | None:
        """LMOVE atómico: saca de pendiente → pasa a inflight. Retorna el mensaje o None."""
        key = self._queue_key(device_id)
        inflight_key = self._inflight_key(device_id)

        data = await self.redis.lmove(key, inflight_key, "LEFT", "RIGHT")
        if data is None:
            return None

        try:
            return json.loads(data)
        except Exception as e:
            logger.error(f"[QUEUE] Error parseando mensaje de cola para {device_id}: {e}")
            # Si el mensaje está corrupto, removerlo de inflight
            await self.redis.lrem(inflight_key, 1, data)
            return None

    async def confirm(self, device_id: str, raw_message: str) -> bool:
        """Confirma entrega: remueve el mensaje de inflight."""
        inflight_key = self._inflight_key(device_id)
        removed = await self.redis.lrem(inflight_key, 1, raw_message)
        return removed > 0

    async def recover_inflight(self, device_id: str) -> int:
        """LMOVE todos los inflight de vuelta a queue (en disconnect). Retorna cantidad."""
        key = self._queue_key(device_id)
        inflight_key = self._inflight_key(device_id)
        count = 0
        while await self.redis.llen(inflight_key) > 0:
            data = await self.redis.lmove(inflight_key, key, "LEFT", "RIGHT")
            if data:
                count += 1
        if count > 0:
            logger.info(f"[QUEUE] {count} mensajes recuperados de inflight para {device_id}")
        return count

    async def get_queue_size(self, device_id: str) -> dict:
        """Retorna estadísticas de cola para un dispositivo."""
        key = self._queue_key(device_id)
        inflight_key = self._inflight_key(device_id)
        queue_len = await self.redis.llen(key)
        inflight_len = await self.redis.llen(inflight_key)
        return {
            "pending": queue_len,
            "inflight": inflight_len,
            "total": queue_len + inflight_len,
        }

    async def get_all_stats(self) -> dict[str, dict]:
        """Retorna estadísticas de todos los dispositivos con cola."""
        pattern = f"{self.QUEUE_PREFIX}:*"
        stats = {}
        seen_devices = set()

        async for key in self.redis.scan_iter(match=pattern):
            # Extraer device_id de la key
            parts = key.split(":")
            if len(parts) >= 3:
                device_id = parts[2]
                if device_id not in seen_devices:
                    seen_devices.add(device_id)
                    try:
                        stats[device_id] = await self.get_queue_size(device_id)
                    except Exception:
                        pass

        return stats

    async def cleanup_old_messages(self) -> int:
        """Elimina mensajes con más de MAX_MESSAGE_AGE. Retorna cantidad limpiada."""
        import time
        cutoff = time.time() - self.MAX_MESSAGE_AGE
        cleaned = 0
        pattern = f"{self.QUEUE_PREFIX}:*"

        async for key in self.redis.scan_iter(match=pattern):
            # Solo procesar keys queue (no inflight)
            if key.endswith(f":{self.INFLIGHT_SUFFIX}"):
                continue
            try:
                # Leer todos los mensajes, filtrar antiguos, re-escribir
                messages = await self.redis.lrange(key, 0, -1)
                if not messages:
                    continue
                valid = []
                for msg in messages:
                    try:
                        parsed = json.loads(msg)
                        msg_time = parsed.get("enqueued_at", 0)
                        if msg_time > 0 and msg_time < cutoff:
                            cleaned += 1
                        else:
                            valid.append(msg)
                    except Exception:
                        valid.append(msg)
                # Re-escribir la lista completa
                if len(valid) != len(messages):
                    device_id = key.split(":")[2]
                    queue_key = self._queue_key(device_id)
                    await self.redis.delete(queue_key)
                    if valid:
                        await self.redis.rpush(queue_key, *valid)
            except Exception as e:
                logger.error(f"[QUEUE] Error limpiando cola {key}: {e}")

        if cleaned > 0:
            logger.info(f"[QUEUE] {cleaned} mensajes antiguos limpiados de Redis")
        return cleaned

    async def set_pending_sync(self, device_id: str) -> None:
        """Marca que un dispositivo tiene sync pendiente."""
        key = f"{self.PENDING_SYNC_PREFIX}:{device_id}"
        await self.redis.set(key, "true", ex=3600)  # 1 hora TTL

    async def check_pending_sync(self, device_id: str) -> bool:
        """Verifica si hay sync pendiente y limpia el flag."""
        key = f"{self.PENDING_SYNC_PREFIX}:{device_id}"
        val = await self.redis.get(key)
        if val == "true":
            await self.redis.delete(key)
            return True
        return False

    async def set_pending_reboot(self, device_id: str, payload: dict) -> None:
        """Guarda un comando REINICIAR pendiente."""
        key = f"{self.PENDING_REBOOT_PREFIX}:{device_id}"
        await self.redis.set(key, json.dumps(payload), ex=3600)

    async def check_pending_reboot(self, device_id: str) -> dict | None:
        """Verifica y recupera un REINICIAR pendiente."""
        key = f"{self.PENDING_REBOOT_PREFIX}:{device_id}"
        data = await self.redis.get(key)
        if data:
            await self.redis.delete(key)
            try:
                return json.loads(data)
            except Exception:
                return {"command": "REINICIAR"}
        return None

    async def consume_pending_banner(self, device_id: str) -> dict | None:
        """Consume un banner pendiente de la key legacy device:pending:banner:*."""
        key = f"{self.PENDING_BANNER_PREFIX}:{device_id}"
        data = await self.redis.get(key)
        if data:
            await self.redis.delete(key)
            try:
                return json.loads(data)
            except Exception:
                pass
        return None

    async def flush_all_to_device(self, device_id: str, send_fn) -> int:
        """Envía todos los mensajes pendientes al dispositivo via send_fn.
        send_fn es un callable async que recibe (message: dict) y retorna True/False.
        Retorna cantidad de mensajes entregados exitosamente.
        """
        delivered = 0
        failed_raws = []

        while True:
            msg = await self.dequeue(device_id)
            if msg is None:
                break

            raw = json.dumps(msg)
            try:
                success = await send_fn(msg)
                if success:
                    await self.confirm(device_id, raw)
                    delivered += 1
                else:
                    failed_raws.append(raw)
                    break
            except Exception as e:
                logger.warning(f"[QUEUE] Error enviando a {device_id}: {e}")
                failed_raws.append(raw)
                break

        # Re-encolar los que fallaron
        for raw in failed_raws:
            try:
                await self.redis.lpush(self._queue_key(device_id), raw)
            except Exception:
                pass

        if delivered > 0:
            logger.info(f"[QUEUE] {delivered} mensajes entregados de cola Redis a {device_id}")
        return delivered

    async def close(self) -> None:
        await self.redis.close()


pending_queue: PendingCommandQueue | None = None
