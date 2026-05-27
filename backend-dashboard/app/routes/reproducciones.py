import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.services.metricas_service import resumen_diario, resumen_por_sede, tendencia_14d, get_venezuela_now

router = APIRouter(prefix="/reproducciones", tags=["reproducciones"])
logger = logging.getLogger("uvicorn.error")


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


@router.get("/por-sede")
async def obtener_reproducciones_por_sede(
    fecha: str | None = Query(None, description="Fecha en formato YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    try:
        target_date = date.fromisoformat(fecha) if fecha else get_venezuela_now().date()
        sedes = await resumen_por_sede(db, target_date)
        return {"success": True, "fecha": target_date.isoformat(), "sedes": sedes}
    except Exception as e:
        logger.error(f"Error en por-sede: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
