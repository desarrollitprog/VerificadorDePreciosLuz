from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis


class DeviceStateStore:
    def __init__(self, redis: Redis, heartbeat_ttl: int = 120):
        self.redis = redis
        self.heartbeat_ttl = heartbeat_ttl

    @classmethod
    async def create(cls) -> "DeviceStateStore":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        heartbeat_ttl = int(os.getenv("DEVICE_HEARTBEAT_TTL", "120"))
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, heartbeat_ttl=heartbeat_ttl)

    async def close(self) -> None:
        await self.redis.close()

    async def upsert_heartbeat(self, device_id: str, server_id: str | None = None) -> None:
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
        pipe.expire(key, self.heartbeat_ttl)
        await pipe.execute()

    async def mark_offline(self, device_id: str) -> None:
        key = f"device:state:{device_id}"
        if await self.redis.exists(key):
            await self.redis.hset(key, mapping={"online": "0"})

    async def get_all_status(self) -> dict[str, dict[str, Any]]:
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

            result[device_id] = {
                "online": is_online_by_ttl,
                "last_seen": row.get("last_seen"),
                "server_id": row.get("server_id") or None,
            }

        return result
