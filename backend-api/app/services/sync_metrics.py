import asyncio
import json
import logging
import os
import random
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import Integer, select, func, cast

from ..database import AsyncSessionLocalPublicidad
from ..models.reproduccion_metrica import ReproduccionMetricaSede

logger = logging.getLogger("uvicorn.error")

INTERVALO_HORAS = 5
STAGGER_MAX_SEGUNDOS = 300
DASHBOARD_URL = os.getenv("DASHBOARD_URL").rstrip("/")
SYNC_URL = f"{DASHBOARD_URL}/api/reproducciones/sincronizar"


async def sincronizar_metricas(servidor_id: int):
    """Worker que cada 5h agrega datos por banner y los envía al dashboard."""
    while True:
        try:
            stagger = random.uniform(0, STAGGER_MAX_SEGUNDOS)
            await asyncio.sleep((INTERVALO_HORAS * 3600) + stagger)

            hoy = datetime.now(timezone(timedelta(hours=-4))).date()
            inicio_hoy = datetime(hoy.year, hoy.month, hoy.day, tzinfo=timezone(timedelta(hours=-4)))
            inicio_utc = inicio_hoy.astimezone(timezone.utc).replace(tzinfo=None)

            banners = []
            async with AsyncSessionLocalPublicidad() as db:
                stmt = (
                    select(
                        ReproduccionMetricaSede.banner_id,
                        ReproduccionMetricaSede.titulo,
                        ReproduccionMetricaSede.tipo_dispositivo,
                        func.count(ReproduccionMetricaSede.id).label("reproducciones"),
                        func.sum(
                            cast(ReproduccionMetricaSede.completo, Integer)
                        ).label("completados"),
                        func.sum(
                            cast(ReproduccionMetricaSede.cuartil_50, Integer)
                        ).label("validas_50"),
                        func.coalesce(
                            func.sum(ReproduccionMetricaSede.segundos_reproducidos), 0
                        ).label("segundos"),
                    )
                    .where(ReproduccionMetricaSede.fecha_creacion >= inicio_utc)
                    .group_by(
                        ReproduccionMetricaSede.banner_id,
                        ReproduccionMetricaSede.titulo,
                        ReproduccionMetricaSede.tipo_dispositivo,
                    )
                )
                rows = (await db.execute(stmt)).all()
                for row in rows:
                    banners.append({
                        "banner_id": row.banner_id,
                        "titulo": row.titulo or "Sin título",
                        "tipo_dispositivo": row.tipo_dispositivo or "verificador",
                        "reproducciones": row.reproducciones or 0,
                        "completados": row.completados or 0,
                        "validas_50": row.validas_50 or 0,
                        "segundos": float(row.segundos or 0),
                    })

            if not banners:
                logger.info("[SyncMetrics] No hay datos para sincronizar")
                continue

            payload = {
                "servidor_id": servidor_id,
                "fecha": hoy.isoformat(),
                "banners": banners,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(SYNC_URL, json=payload)

            if resp.status_code == 200:
                logger.info(
                    f"[SyncMetrics] Sincronizados {len(banners)} banners "
                    f"de servidor {servidor_id}"
                )
            else:
                logger.warning(
                    f"[SyncMetrics] Dashboard respondió {resp.status_code}, "
                    f"reintentando en {INTERVALO_HORAS}h"
                )

        except httpx.ConnectError:
            logger.warning(
                f"[SyncMetrics] Dashboard no disponible, reintentando "
                f"en {INTERVALO_HORAS}h"
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[SyncMetrics] Error en ciclo: {e}")
