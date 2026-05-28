import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.models.metricas_por_sede import MetricasPorSede

router = APIRouter(prefix="/reproducciones", tags=["reproducciones"])
logger = logging.getLogger("uvicorn.error")


class BannerSyncItem(BaseModel):
    banner_id: int
    titulo: str | None = None
    tipo_dispositivo: str | None = None
    reproducciones: int = 0
    completados: int = 0
    validas_50: int = 0
    segundos: float = 0


class SyncPayload(BaseModel):
    servidor_id: int
    fecha: str
    banners: list[BannerSyncItem]


@router.post("/sincronizar")
async def recibir_sync(body: SyncPayload, db: AsyncSession = Depends(get_db_usuarios)):
    try:
        target_date = date.fromisoformat(body.fecha)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    rows = []
    for b in body.banners:
        rows.append({
            "servidor_id": body.servidor_id,
            "banner_id": b.banner_id,
            "titulo": b.titulo,
            "fecha": target_date,
            "tipo_dispositivo": b.tipo_dispositivo or "verificador",
            "reproducciones": b.reproducciones,
            "completados": b.completados,
            "validas_50": b.validas_50,
            "segundos_totales": b.segundos,
        })

    if not rows:
        return {"success": True, "insertados": 0}

    async with db.begin():
        await db.execute(
            delete(MetricasPorSede).where(
                MetricasPorSede.servidor_id == body.servidor_id,
                MetricasPorSede.fecha == target_date,
            )
        )
        await db.execute(insert(MetricasPorSede), rows)

    logger.info(
        f"Sincronizados {len(rows)} banners de servidor {body.servidor_id} para {target_date}"
    )
    return {"success": True, "insertados": len(rows)}
