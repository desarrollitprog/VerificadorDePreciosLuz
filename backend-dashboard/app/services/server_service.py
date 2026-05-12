from datetime import datetime
from typing import Any
import logging
import httpx

logger = logging.getLogger("uvicorn.error")

HEARTBEAT_OFFLINE_MINUTES = 8


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


async def _obtener_dispositivos_de_servidor(ip: str) -> list[dict[str, Any]]:
    url = f"http://{ip}:8000/devices/status"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        if not isinstance(payload, dict):
            return []

        dispositivos: list[dict[str, Any]] = []
        for device_id, info in payload.items():
            if not isinstance(info, dict):
                continue
            dispositivos.append(
                {
                    "device_id": str(device_id),
                    "online": bool(info.get("online", False)),
                    "last_seen": info.get("last_seen"),
                    "server_id": info.get("server_id"),
                }
            )

        dispositivos.sort(key=lambda d: d["device_id"])
        logger.info("status-detalle: %s reportó %s dispositivos", ip, len(dispositivos))
        return dispositivos
    except Exception as e:
        logger.warning("status-detalle: fallo consultando %s: %s", url, e)
        return []


async def _obtener_conteo_videos_servidor(ip: str) -> int:
    url = f"http://{ip}:8000/banners"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        if isinstance(payload, list):
            return len(payload)
        return 0
    except Exception as e:
        logger.warning("videos-servidor: fallo consultando %s: %s", url, e)
        return 0
