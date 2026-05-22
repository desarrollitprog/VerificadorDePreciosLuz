import logging
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.models.reproduccion_metrica import ReproduccionMetrica
from app.models.dispositivo import Dispositivo
from app.services.metricas_service import resumen_diario, tendencia_14d

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
    db: AsyncSession = Depends(get_db_usuarios),
):
    try:
        count = 0
        for ev in body.eventos:
            now = datetime.utcnow()
            stmt = select(ReproduccionMetrica).where(
                ReproduccionMetrica.reproduccion_id == ev.reproduccion_id
            )
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if existing is None:
                if ev.tipo_evento not in ("START", "COMPLETED", "INTERRUPTED"):
                    continue
                nueva = ReproduccionMetrica(
                    reproduccion_id=ev.reproduccion_id,
                    dispositivo_id=ev.dispositivo_id,
                    banner_id=ev.banner_id,
                    titulo=ev.titulo,
                    duracion_total_seg=ev.duracion_total_seg,
                    inicio_reproduccion=now if ev.tipo_evento == "START" else None,
                    segundos_reproducidos=ev.segundos_reproducidos,
                    porcentaje_completado=ev.porcentaje_completado,
                    cuartil_50=ev.cuartil_50 or False,
                    cuartil_75=ev.cuartil_75 or False,
                    cuartil_100=ev.cuartil_100 or False,
                    completo=ev.completo or False,
                    motivo_fin=ev.motivo_fin,
                    fecha_creacion=now,
                )
                if ev.tipo_evento in ("COMPLETED", "INTERRUPTED"):
                    nueva.fin_reproduccion = now
                db.add(nueva)
                count += 1
            else:
                if ev.tipo_evento == "START" and existing.inicio_reproduccion is None:
                    existing.inicio_reproduccion = now
                if ev.titulo and not existing.titulo:
                    existing.titulo = ev.titulo
                if ev.duracion_total_seg is not None:
                    existing.duracion_total_seg = ev.duracion_total_seg
                if ev.segundos_reproducidos is not None and (existing.segundos_reproducidos is None or ev.segundos_reproducidos > existing.segundos_reproducidos):
                    existing.segundos_reproducidos = ev.segundos_reproducidos
                if ev.porcentaje_completado is not None and (existing.porcentaje_completado is None or ev.porcentaje_completado > existing.porcentaje_completado):
                    existing.porcentaje_completado = ev.porcentaje_completado
                if ev.cuartil_50:
                    existing.cuartil_50 = True
                if ev.cuartil_75:
                    existing.cuartil_75 = True
                if ev.cuartil_100:
                    existing.cuartil_100 = True
                if ev.completo:
                    existing.completo = True
                if ev.motivo_fin:
                    existing.motivo_fin = ev.motivo_fin
                if ev.tipo_evento in ("COMPLETED", "INTERRUPTED"):
                    existing.fin_reproduccion = now
                count += 1

        await db.commit()
        return {"success": True, "procesados": count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error procesando batch reproducciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando batch: {e}")


@router.get("/resumen-diario")
async def obtener_resumen_diario(
    fecha: str | None = Query(None, description="Fecha en formato YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        target_date = date.fromisoformat(fecha) if fecha else date.today()
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
