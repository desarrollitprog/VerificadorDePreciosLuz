from __future__ import annotations

import os
import json
from datetime import datetime, timedelta

from redis.asyncio import Redis


class DeviceRegistry:
    def __init__(self, redis: Redis, ttl_seconds: int = 300):
        self.redis = redis
        self.key_prefix = "device:registry:"
        self.ttl_seconds = ttl_seconds

    @classmethod
    async def create(cls, ttl_seconds: int = 300) -> "DeviceRegistry":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, ttl_seconds=ttl_seconds)

    async def register_device(self, device_id: str) -> None:
        key = f"{self.key_prefix}{device_id}"
        data = {
            "device_id": device_id,
            "registered_at": datetime.utcnow().isoformat(),
        }
        await self.redis.set(key, json.dumps(data), ex=self.ttl_seconds)

    async def unregister_device(self, device_id: str) -> None:
        key = f"{self.key_prefix}{device_id}"
        await self.redis.delete(key)

    async def extend_ttl(self, device_id: str) -> None:
        key = f"{self.key_prefix}{device_id}"
        await self.redis.expire(key, self.ttl_seconds)

    async def is_device_registered(self, device_id: str) -> bool:
        key = f"{self.key_prefix}{device_id}"
        return await self.redis.exists(key) > 0

    async def get_all_registered_devices(self) -> list[str]:
        pattern = f"{self.key_prefix}*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        
        devices = []
        for key in keys:
            device_id = key.replace(self.key_prefix, "")
            devices.append(device_id)
        return devices


async def get_connected_devices() -> list[str]:
    global device_registry
    if device_registry is None:
        return []
    return await device_registry.get_all_registered_devices()


async def register_device(device_id: str) -> None:
    global device_registry
    if device_registry is not None:
        await device_registry.register_device(device_id)


async def unregister_device(device_id: str) -> None:
    global device_registry
    if device_registry is not None:
        await device_registry.unregister_device(device_id)


async def extend_device_ttl(device_id: str) -> None:
    global device_registry
    if device_registry is not None:
        await device_registry.extend_ttl(device_id)


device_registry: DeviceRegistry | None = None
