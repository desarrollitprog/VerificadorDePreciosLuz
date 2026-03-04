from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.models import Notificacion, NotificacionLeida
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
    user_id = current_user.get("user_id") if current_user else None
    if user_id is None:
        return {
            "success": False,
            "notificaciones": [],
            "limit": limit,
            "offset": offset,
            "count": 0,
            "unread_count": 0,
        }

    read_count_stmt = select(func.count()).select_from(NotificacionLeida).where(NotificacionLeida.usuario_id == user_id)
    read_count_result = await db.execute(read_count_stmt)
    read_count = int(read_count_result.scalar() or 0)

    total_count_stmt = select(func.count()).select_from(Notificacion)
    total_count_result = await db.execute(total_count_stmt)
    total_count = int(total_count_result.scalar() or 0)

    unread_count = max(total_count - read_count, 0)

    stmt = (
        select(Notificacion)
        .options(selectinload(Notificacion.usuario))
        .order_by(Notificacion.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    notificaciones = result.scalars().all()

    notification_ids = [n.id for n in notificaciones]
    leidas_ids: set[int] = set()
    if notification_ids:
        read_stmt = select(NotificacionLeida.notificacion_id).where(
            NotificacionLeida.usuario_id == user_id,
            NotificacionLeida.notificacion_id.in_(notification_ids),
        )
        read_result = await db.execute(read_stmt)
        leidas_ids = set(read_result.scalars().all())

    return {
        "success": True,
        "notificaciones": [
            {
                **n.__dict__,
                "leida": n.id in leidas_ids,
                "nombre_usuario": n.usuario.nombre_usuario if n.usuario else None
            }
            for n in notificaciones
        ],
        "limit": limit,
        "offset": offset,
        "count": len(notificaciones),
        "unread_count": unread_count,
    }


@router.patch("/notificaciones/marcar-leidas")
async def marcar_notificaciones_leidas(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    if user_id is None:
        return {"success": False, "updated": 0}

    all_ids_result = await db.execute(select(Notificacion.id))
    all_ids = all_ids_result.scalars().all()

    if not all_ids:
        return {"success": True, "updated": 0}

    read_ids_result = await db.execute(
        select(NotificacionLeida.notificacion_id).where(
            NotificacionLeida.usuario_id == user_id,
        )
    )
    read_ids = set(read_ids_result.scalars().all())

    to_mark = [
        NotificacionLeida(usuario_id=user_id, notificacion_id=notification_id)
        for notification_id in all_ids
        if notification_id not in read_ids
    ]

    if to_mark:
        db.add_all(to_mark)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Si hubo solicitudes concurrentes, la restricción única puede dispararse;
        # tratamos el endpoint como idempotente y devolvemos éxito.
        return {
            "success": True,
            "updated": 0,
        }

    return {
        "success": True,
        "updated": len(to_mark),
    }
# Modelo para la notificación de sincronización
class SyncStatusBody(BaseModel):
    device_id: str
    status: str
    reason: str = ""


class PlaybackStatusBody(BaseModel):
    device_id: str
    video_name: str
    reason: str = ""

@router.post("/sync-status", status_code=status.HTTP_201_CREATED)
async def sync_status(
    body: SyncStatusBody,
    db: AsyncSession = Depends(get_db_usuarios),
):
    # Registrar la notificación en la base de datos (con deduplicación temporal)
    reason = (body.reason or "").strip() or "sin detalle"
    descripcion = f"Dispositivo {body.device_id} falló sincronización: {reason}"

    dedupe_since = datetime.utcnow() - timedelta(seconds=120)
    recent_stmt = (
        select(Notificacion)
        .where(
            Notificacion.tipo == "SYNC_FAILED",
            Notificacion.descripcion == descripcion,
            Notificacion.fecha_creacion >= dedupe_since,
        )
        .order_by(Notificacion.fecha_creacion.desc())
        .limit(1)
    )
    recent_result = await db.execute(recent_stmt)
    existing = recent_result.scalars().first()

    if existing:
        return {
            "success": True,
            "message": "Notificación SYNC_FAILED ya registrada recientemente.",
            "duplicated": True,
            "id": existing.id,
        }

    await registrar_accion(
        db=db,
        usuario_id=None,
        tipo="SYNC_FAILED",
        descripcion=descripcion,
    )
    return {"success": True, "message": "Notificación de sincronización registrada", "duplicated": False}


@router.post("/playback-status", status_code=status.HTTP_201_CREATED)
async def playback_status(
    body: PlaybackStatusBody,
    db: AsyncSession = Depends(get_db_usuarios),
):
    reason = (body.reason or "").strip() or "sin detalle"
    video_name = (body.video_name or "").strip() or "(sin nombre)"
    descripcion = f"Dispositivo {body.device_id} no pudo reproducir '{video_name}': {reason}"

    dedupe_since = datetime.utcnow() - timedelta(seconds=120)
    recent_stmt = (
        select(Notificacion)
        .where(
            Notificacion.tipo == "PLAYBACK_FAILED",
            Notificacion.descripcion == descripcion,
            Notificacion.fecha_creacion >= dedupe_since,
        )
        .order_by(Notificacion.fecha_creacion.desc())
        .limit(1)
    )
    recent_result = await db.execute(recent_stmt)
    existing = recent_result.scalars().first()

    if existing:
        return {
            "success": True,
            "message": "Notificación PLAYBACK_FAILED ya registrada recientemente.",
            "duplicated": True,
            "id": existing.id,
        }

    await registrar_accion(
        db=db,
        usuario_id=None,
        tipo="PLAYBACK_FAILED",
        descripcion=descripcion,
    )
    return {
        "success": True,
        "message": "Notificación de error de reproducción registrada",
        "duplicated": False,
    }
