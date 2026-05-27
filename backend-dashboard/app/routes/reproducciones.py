import logging
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.services.metrics_redis import get_metrics_redis, BULK_KEY, MAX_BULK_EVENTS
from app.dependencies import get_current_cliente
from app.models.reproduccion_metrica import ReproduccionMetrica
from app.models.dispositivo import Dispositivo
from app.services.metricas_service import resumen_diario, tendencia_14d, get_venezuela_now

router = APIRouter(prefix="/reproducciones", tags=["reproducciones"])
logger = logging.getLogger("uvicorn.error")


class EventoProgreso(BaseModel):
    reproduccion_id: str
    dispositivo_id: str
    banner_id: int
    titulo: str | None = None
    tipo_evento: str
    duracion_total_seg: float | None = None
    segundos_reproducidos: float | None = None
    porcentaje_completado: float | None = None
    cuartil_50: bool | None = None
    cuartil_75: bool | None = None
    cuartil_100: bool | None = None
    completo: bool | None = None
    motivo_fin: str | None = None
    _ts: str | None = None


class BatchProgresoBody(BaseModel):
    eventos: list[EventoProgreso]


@router.post("/batch")
async def recibir_batch_reproducciones(
    body: BatchProgresoBody,
):
    redis_client = await get_metrics_redis()
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis no disponible")
    eventos_json = [ev.json() for ev in body.eventos]
    await redis_client.rpush(BULK_KEY, *eventos_json)
    llenado = await redis_client.llen(BULK_KEY)
    if llenado > MAX_BULK_EVENTS:
        exceso = llenado - MAX_BULK_EVENTS
        await redis_client.ltrim(BULK_KEY, exceso, -1)
        logger.warning(f"Cola {BULK_KEY} excedió límite ({llenado} > {MAX_BULK_EVENTS}), descartados {exceso} eventos antiguos")
    logger.info(f"Batch recibido: {len(eventos_json)} eventos encolados en Redis")
    return {"success": True, "procesados": len(eventos_json)}


@router.get("/resumen-diario")
async def obtener_resumen_diario(
    fecha: str | None = Query(None, description="Fecha en formato YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        target_date = date.fromisoformat(fecha) if fecha else get_venezuela_now().date()
        resumen = await resumen_diario(db, target_date)
        tendencia = await tendencia_14d(db, target_date)
        return {
            "success": True,
            "fecha": target_date.isoformat(),
            "resumen": resumen,
            "tendencia_14d": tendencia,
        }
    except Exception as e:
        logger.error(f"Error en resumen-diario: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
