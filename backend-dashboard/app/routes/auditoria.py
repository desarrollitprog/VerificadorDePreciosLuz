from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.sql import literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_usuarios
from app.dependencies import get_current_admin
from app.models.notificacion import Notificacion
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.dispositivo import Dispositivo
from app.models.servidor_secundario import ServidorSecundario


router = APIRouter(tags=["auditoria"])
logger = logging.getLogger("uvicorn.error")


def _to_venezuela_time(dt: datetime) -> datetime:
    """Convierte datetime UTC a timezone de Venezuela (UTC-4)"""
    if dt is None:
        return None
    return dt - timedelta(hours=4)


class AuditoriaItem(BaseModel):
    id: int
    fecha: str
    tipo: str
    descripcion: str
    dispositivo_id: Optional[str] = None
    dispositivo_nombre: Optional[str] = None
    servidor_id: Optional[int] = None
    servidor_nombre: Optional[str] = None
    sesion_inicio: Optional[str] = None
    sesion_fin: Optional[str] = None
    duracion_segundos: Optional[int] = None
    usuario: Optional[str] = None
    origen: str


class AuditoriaFilter(BaseModel):
    busqueda: Optional[str] = None
    tipo: Optional[str] = None
    dispositivo_id: Optional[str] = None
    servidor_id: Optional[int] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    page: int = 1
    limit: int = 20


@router.get("/auditoria")
async def obtener_auditoria(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
    busqueda: str = Query(None, description="Texto a buscar"),
    tipo: str = Query(None, description="Tipo de evento"),
    dispositivo_id: str = Query(None, description="ID del dispositivo"),
    servidor_id: int = Query(None, description="ID del servidor"),
    fecha_desde: datetime = Query(None, description="Fecha desde"),
    fecha_hasta: datetime = Query(None, description="Fecha hasta"),
    page: int = Query(1, ge=1, description="Página"),
    limit: int = Query(20, ge=1, le=100, description="Límite por página"),
):
    """
    Obtiene el historial de auditoría combinando notificaciones y sesiones de dispositivos.
    Optimizado: consultas separadas con paginación SQL.
    """
    offset = (page - 1) * limit
    
    sesion_conditions = []
    if tipo:
        sesion_conditions.append(
            case(
                (DispositivoSesion.fin.is_(None), "CONEXION_DISPOSITIVO"),
                else_="DESCONEXION_DISPOSITIVO"
            ) == tipo
        )
    if dispositivo_id:
        sesion_conditions.append(Dispositivo.codigo_kiosko == dispositivo_id)
    if servidor_id:
        sesion_conditions.append(ServidorSecundario.id == servidor_id)
    if fecha_desde:
        sesion_conditions.append(DispositivoSesion.inicio >= fecha_desde)
    if fecha_hasta:
        sesion_conditions.append(DispositivoSesion.inicio <= fecha_hasta)
    
    sesion_count_query = (
        select(func.count(DispositivoSesion.id))
        .select_from(DispositivoSesion)
        .outerjoin(Dispositivo, Dispositivo.codigo_kiosko == DispositivoSesion.dispositivo_id)
        .outerjoin(ServidorSecundario, ServidorSecundario.id == Dispositivo.servidor_id)
    )
    if sesion_conditions:
        sesion_count_query = sesion_count_query.where(*sesion_conditions)
    sesion_count_result = await db.execute(sesion_count_query)
    sesion_total = sesion_count_result.scalar() or 0
    
    notif_conditions = []
    if tipo:
        notif_conditions.append(Notificacion.tipo == tipo)
    if dispositivo_id:
        notif_conditions.append(Notificacion.dispositivo_id == dispositivo_id)
    if servidor_id:
        notif_conditions.append(Notificacion.servidor_id == servidor_id)
    if fecha_desde:
        notif_conditions.append(Notificacion.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        notif_conditions.append(Notificacion.fecha_creacion <= fecha_hasta)
    
    notif_count_query = (
        select(func.count(Notificacion.id))
        .select_from(Notificacion)
    )
    if notif_conditions:
        notif_count_query = notif_count_query.where(*notif_conditions)
    notif_count_result = await db.execute(notif_count_query)
    notif_total = notif_count_result.scalar() or 0
    
    total = sesion_total + notif_total
    
    sesion_query = (
        select(
            DispositivoSesion.id,
            DispositivoSesion.inicio.label("fecha"),
            case(
                (DispositivoSesion.fin.is_(None), "CONEXION_DISPOSITIVO"),
                else_="DESCONEXION_DISPOSITIVO"
            ).label("tipo"),
            case(
                (DispositivoSesion.fin.is_(None),
                 func.concat(
                     "Dispositivo '",
                     func.coalesce(Dispositivo.nombre_amigable, Dispositivo.codigo_kiosko),
                     "' (",
                     Dispositivo.codigo_kiosko,
                     ") conectado al servidor '",
                     func.coalesce(ServidorSecundario.nombre, "Desconocido"),
                     "'"
                 )),
                else_=func.concat(
                    "Dispositivo '",
                    func.coalesce(Dispositivo.nombre_amigable, Dispositivo.codigo_kiosko),
                    "' (",
                    Dispositivo.codigo_kiosko,
                    ") desconectado del servidor '",
                    func.coalesce(ServidorSecundario.nombre, "Desconocido"),
                    "'. Duración: ",
                    DispositivoSesion.duracion_segundos
                )
            ).label("descripcion"),
            Dispositivo.codigo_kiosko.label("dispositivo_id"),
            Dispositivo.nombre_amigable.label("dispositivo_nombre"),
            ServidorSecundario.id.label("servidor_id"),
            ServidorSecundario.nombre.label("servidor_nombre"),
            DispositivoSesion.inicio.label("sesion_inicio"),
            DispositivoSesion.fin.label("sesion_fin"),
            DispositivoSesion.duracion_segundos,
            literal_column("NULL").label("usuario"),
            literal_column("'sesion'").label("origen"),
        )
        .select_from(DispositivoSesion)
        .outerjoin(Dispositivo, Dispositivo.codigo_kiosko == DispositivoSesion.dispositivo_id)
        .outerjoin(ServidorSecundario, ServidorSecundario.id == Dispositivo.servidor_id)
    )
    
    sesion_offset = offset
    sesion_limit = limit
    
    if offset >= sesion_total:
        sesion_offset = 0
        sesion_limit = 0
    elif offset + limit > sesion_total:
        sesion_limit = sesion_total - offset
    
    if sesion_limit > 0:
        sesion_query = sesion_query.order_by(DispositivoSesion.inicio.desc()).offset(sesion_offset).limit(sesion_limit)
    
    sesion_result = await db.execute(sesion_query)
    sesion_rows = sesion_result.all()
    
    remaining_offset = max(0, offset - sesion_total)
    remaining_limit = limit - len(sesion_rows)
    
    notif_query = (
        select(
            Notificacion.id,
            Notificacion.fecha_creacion.label("fecha"),
            Notificacion.tipo,
            func.coalesce(Notificacion.descripcion, "").label("descripcion"),
            Notificacion.dispositivo_id,
            Notificacion.servidor_id,
            Notificacion.usuario_id,
            literal_column("'notificacion'").label("origen"),
        )
        .select_from(Notificacion)
    )
    
    if remaining_limit > 0:
        notif_query = notif_query.order_by(Notificacion.fecha_creacion.desc()).offset(remaining_offset).limit(remaining_limit)
    
    notif_result = await db.execute(notif_query)
    notif_rows = notif_result.all()
    
    items = []
    
    for row in sesion_rows:
        items.append({
            "id": row.id,
            "fecha": _to_venezuela_time(row.fecha).isoformat() if row.fecha else None,
            "tipo": row.tipo,
            "descripcion": row.descripcion,
            "dispositivo_id": row.dispositivo_id,
            "dispositivo_nombre": row.dispositivo_nombre,
            "servidor_id": row.servidor_id,
            "servidor_nombre": row.servidor_nombre,
            "sesion_inicio": _to_venezuela_time(row.sesion_inicio).isoformat() if row.sesion_inicio else None,
            "sesion_fin": _to_venezuela_time(row.sesion_fin).isoformat() if row.sesion_fin else None,
            "duracion_segundos": row.duracion_segundos,
            "usuario": row.usuario,
            "origen": row.origen,
        })
    
    for row in notif_rows:
        usuario_str = str(row.usuario_id) if row.usuario_id else None
        items.append({
            "id": row.id,
            "fecha": _to_venezuela_time(row.fecha).isoformat() if row.fecha else None,
            "tipo": row.tipo,
            "descripcion": row.descripcion,
            "dispositivo_id": row.dispositivo_id,
            "dispositivo_nombre": None,
            "servidor_id": row.servidor_id,
            "servidor_nombre": None,
            "sesion_inicio": None,
            "sesion_fin": None,
            "duracion_segundos": None,
            "usuario": usuario_str,
            "origen": row.origen,
        })
    
    items.sort(key=lambda x: x.get("fecha") or "", reverse=True)
    
    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
    }
