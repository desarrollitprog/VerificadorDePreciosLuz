from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, delete, func, literal
from sqlalchemy.exc import IntegrityError
from app.models import Notificacion, NotificacionLeida
from app.models.usuario import Usuario
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.services.notificacion_service import registrar_accion
from pydantic import BaseModel

router = APIRouter()

@router.get("/notificaciones")
async def listar_notificaciones(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    solo_no_leidas: bool = Query(False),
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

    unread_count_stmt = (
        select(func.count(Notificacion.id))
        .select_from(Notificacion)
        .outerjoin(
            NotificacionLeida,
            and_(
                NotificacionLeida.notificacion_id == Notificacion.id,
                NotificacionLeida.usuario_id == user_id,
            ),
        )
        .where(NotificacionLeida.notificacion_id.is_(None))
    )
    unread_count_result = await db.execute(unread_count_stmt)
    unread_count = int(unread_count_result.scalar() or 0)

    stmt = (
        select(Notificacion, Usuario.nombre_usuario.label("nombre_usuario"))
        .outerjoin(Usuario, Usuario.id == Notificacion.usuario_id)
        .order_by(Notificacion.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
    )
    if solo_no_leidas:
        stmt = stmt.outerjoin(
            NotificacionLeida,
            and_(
                NotificacionLeida.notificacion_id == Notificacion.id,
                NotificacionLeida.usuario_id == user_id,
            ),
        ).where(NotificacionLeida.notificacion_id.is_(None))
    result = await db.execute(stmt)
    rows = result.all()
    notificaciones = [row[0] for row in rows]
    nombres_por_id = {
        row[0].id: row[1]
        for row in rows
    }

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
                "nombre_usuario": nombres_por_id.get(n.id)
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

    subquery_not_leidas = (
        select(Notificacion.id)
        .outerjoin(
            NotificacionLeida,
            and_(
                NotificacionLeida.notificacion_id == Notificacion.id,
                NotificacionLeida.usuario_id == user_id
            )
        )
        .where(NotificacionLeida.id.is_(None))
    ).subquery()

    insert_stmt = (
        NotificacionLeida.__table__.insert()
        .from_select(
            ['usuario_id', 'notificacion_id'],
            select(
                literal(user_id).label('usuario_id'),
                subquery_not_leidas.c.id.label('notificacion_id')
            )
        )
    )

    try:
        result = await db.execute(insert_stmt)
        await db.commit()
        updated = result.rowcount or 0
    except IntegrityError:
        await db.rollback()
        return {"success": True, "updated": 0}

    return {"success": True, "updated": updated}


@router.delete("/notificaciones/leidas")
async def eliminar_notificaciones_leidas(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    user_id = current_user.get("user_id") if current_user else None
    if user_id is None:
        return {"success": False, "deleted": 0}

    read_count_result = await db.execute(
        select(func.count()).select_from(NotificacionLeida).where(NotificacionLeida.usuario_id == user_id)
    )
    read_count = int(read_count_result.scalar() or 0)

    if read_count == 0:
        return {"success": True, "deleted": 0}

    read_ids_subquery = select(NotificacionLeida.notificacion_id).where(
        NotificacionLeida.usuario_id == user_id
    )

    delete_result = await db.execute(
        delete(Notificacion).where(Notificacion.id.in_(read_ids_subquery))
    )
    await db.commit()

    return {
        "success": True,
        "deleted": int(delete_result.rowcount or 0),
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


class BannerStatusBody(BaseModel):
    device_id: str
    banner_id: int | None = None
    status: str  # "INICIADO" o "FINALIZADO"


@router.post("/banner-status", status_code=status.HTTP_201_CREATED)
async def banner_status(
    body: BannerStatusBody,
    db: AsyncSession = Depends(get_db_usuarios),
):
    tipo = "BANNER_INICIADO" if body.status == "INICIADO" else "BANNER_FINALIZADO"
    
    descripcion = f"Dispositivo {body.device_id}"
    if body.banner_id:
        descripcion += f" - Banner ID {body.banner_id}"
    descripcion += f" - {body.status}"
    
    await registrar_accion(
        db=db,
        usuario_id=None,
        tipo=tipo,
        descripcion=descripcion,
    )
    return {
        "success": True,
        "message": f"Notificación de banner {body.status} registrada",
    }
