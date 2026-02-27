from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Notificacion
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from sqlalchemy.orm import selectinload
from app.services.notificacion_service import registrar_accion
from pydantic import BaseModel

router = APIRouter()

@router.get("/notificaciones")
async def listar_notificaciones(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    stmt = (
        select(Notificacion)
        .options(selectinload(Notificacion.usuario))
        .order_by(Notificacion.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    notificaciones = result.scalars().all()
    return {
        "success": True,
        "notificaciones": [
            {
                **n.__dict__,
                "nombre_usuario": n.usuario.nombre_usuario if n.usuario else None
            }
            for n in notificaciones
        ],
        "limit": limit,
        "offset": offset,
        "count": len(notificaciones)
    }
# Modelo para la notificación de sincronización
class SyncStatusBody(BaseModel):
    device_id: str
    status: str
    reason: str = ""

@router.post("/sync-status", status_code=status.HTTP_201_CREATED)
async def sync_status(
    body: SyncStatusBody,
    db: AsyncSession = Depends(get_db_usuarios),
):
    # Registrar la notificación en la base de datos
    descripcion = f"Dispositivo {body.device_id} falló sincronización: {body.reason}"
    await registrar_accion(
        db=db,
        usuario_id=None,
        tipo="SYNC_FAILED",
        descripcion=descripcion,
    )
    return {"success": True, "message": "Notificación de sincronización registrada"}
