import os
import time
from typing import TypedDict
import redis.asyncio as redis
from sqlalchemy import text
from app.database import engine_usuarios


_redis_client: redis.Redis | None = None


async def get_health_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://dashboard-redis:6380")
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


class HealthStatus(TypedDict):
    status: str
    timestamp: float
    services: dict[str, dict[str, str | bool]]


async def check_database() -> dict[str, str | bool]:
    start = time.perf_counter()
    try:
        async with engine_usuarios.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "unhealthy", "error": str(e), "latency_ms": latency_ms}


async def check_redis() -> dict[str, str | bool]:
    start = time.perf_counter()
    client = await get_health_redis()
    if client is None:
        return {"status": "unavailable", "error": "Redis client not initialized"}
    try:
        await client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "unhealthy", "error": str(e), "latency_ms": latency_ms}


async def get_health_status() -> HealthStatus:
    db_result = await check_database()
    redis_result = await check_redis()

    db_healthy = db_result.get("status") == "healthy"
    redis_healthy = redis_result.get("status") == "healthy"
    overall_healthy = db_healthy

    return HealthStatus(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=time.time(),
        services={
            "database": db_result,
            "redis": redis_result,
        }
    )
