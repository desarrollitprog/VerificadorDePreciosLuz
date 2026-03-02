from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis


class DeviceCommandBus:
    def __init__(self, redis: Redis, command_channel: str, confirmation_channel: str):
        self.redis = redis
        self.command_channel = command_channel
        self.confirmation_channel = confirmation_channel

    @classmethod
    async def create(cls) -> "DeviceCommandBus":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        command_channel = os.getenv("DEVICE_COMMAND_CHANNEL", "device:commands")
        confirmation_channel = os.getenv("DEVICE_CONFIRMATION_CHANNEL", "device:confirmations")

        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis=redis, command_channel=command_channel, confirmation_channel=confirmation_channel)

    async def close(self) -> None:
        await self.redis.close()

    async def publish_command(self, device_id: str, command: str, payload: dict | None = None) -> None:
        message = {
            "device_id": device_id,
            "command": command,
            "payload": payload or {},
        }
        await self.redis.publish(self.command_channel, json.dumps(message))

    async def publish_confirmation(self, device_id: str, command: str, status: str, reason: str = "") -> None:
        message = {
            "device_id": device_id,
            "command": command,
            "status": status,
            "reason": reason,
        }
        await self.redis.publish(self.confirmation_channel, json.dumps(message))

    async def subscribe_forever(
        self,
        on_command: Callable[[str, str, dict], Awaitable[None]],
        on_confirmation: Callable[[str, str, str, str], Awaitable[None]],
    ) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.command_channel, self.confirmation_channel)

        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue

                channel = msg.get("channel")
                raw = msg.get("data")
                if not raw:
                    continue

                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                if channel == self.command_channel:
                    await on_command(
                        str(data.get("device_id", "")),
                        str(data.get("command", "")),
                        data.get("payload") or {},
                    )
                elif channel == self.confirmation_channel:
                    await on_confirmation(
                        str(data.get("device_id", "")),
                        str(data.get("command", "")),
                        str(data.get("status", "")),
                        str(data.get("reason", "")),
                    )
        finally:
            await pubsub.unsubscribe(self.command_channel, self.confirmation_channel)
            await pubsub.close()
