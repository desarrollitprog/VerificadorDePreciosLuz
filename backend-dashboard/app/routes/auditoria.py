from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, literal_column, union_all, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_usuarios
from app.dependencies import get_current_admin
from app.models.notificacion import Notificacion
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.dispositivo import Dispositivo
from app.models.servidor_secundario import ServidorSecundario


router = APIRouter(tags=["auditoria"])
logger = logging.getLogger("uvicorn.error")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


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
    Optimizado: usa paginación SQL nativa en lugar de filtrar en Python.
    """
    offset = (page - 1) * limit
    
    sesion_descripcion = case(
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
    )
    
    sesion_tipo = case(
        (DispositivoSesion.fin.is_(None), "CONEXION_DISPOSITIVO"),
        else_="DESCONEXION_DISPOSITIVO"
    )
    
    sesion_query = (
        select(
            DispositivoSesion.id,
            DispositivoSesion.inicio.label("fecha"),
            sesion_tipo.label("tipo"),
            sesion_descripcion.label("descripcion"),
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
    
    notif_query = (
        select(
            Notificacion.id,
            Notificacion.fecha_creacion.label("fecha"),
            Notificacion.tipo,
            func.coalesce(Notificacion.descripcion, "").label("descripcion"),
            Notificacion.dispositivo_id,
            Dispositivo.nombre_amigable.label("dispositivo_nombre"),
            Notificacion.servidor_id,
            ServidorSecundario.nombre.label("servidor_nombre"),
            literal_column("NULL").label("sesion_inicio"),
            literal_column("NULL").label("sesion_fin"),
            literal_column("NULL").label("duracion_segundos"),
            func.cast(Notificacion.usuario_id, literal_column("VARCHAR(50)")).label("usuario"),
            literal_column("'notificacion'").label("origen"),
        )
        .select_from(Notificacion)
        .outerjoin(Dispositivo, Dispositivo.codigo_kiosko == Notificacion.dispositivo_id)
        .outerjoin(ServidorSecundario, ServidorSecundario.id == Notificacion.servidor_id)
    )
    
    combined = (
        union_all(sesion_query, notif_query)
        .subquery()
    )
    
    filters = []
    if busqueda:
        filters.append(
            or_(
                func.lower(combined.c.descripcion).like(f"%{busqueda.lower()}%"),
                func.lower(combined.c.tipo).like(f"%{busqueda.lower()}%"),
                func.lower(func.coalesce(combined.c.dispositivo_id, "")).like(f"%{busqueda.lower()}%"),
                func.lower(func.coalesce(combined.c.dispositivo_nombre, "")).like(f"%{busqueda.lower()}%"),
                func.lower(func.coalesce(combined.c.servidor_nombre, "")).like(f"%{busqueda.lower()}%")
            )
        )
    if tipo:
        filters.append(combined.c.tipo == tipo)
    if dispositivo_id:
        filters.append(combined.c.dispositivo_id == dispositivo_id)
    if servidor_id:
        filters.append(combined.c.servidor_id == servidor_id)
    if fecha_desde:
        filters.append(combined.c.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(combined.c.fecha <= fecha_hasta)
    
    count_query = select(func.count()).select_from(combined)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = (
        select(combined)
        .order_by(combined.c.fecha.desc())
        .offset(offset)
        .limit(limit)
    )
    if filters:
        query = query.where(*filters)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for row in rows:
        sesion_inicio = row.sesion_inicio
        sesion_fin = row.sesion_fin
        
        items.append({
            "id": row.id,
            "fecha": _to_venezuela_time(row.fecha).isoformat() if row.fecha else None,
            "tipo": row.tipo,
            "descripcion": row.descripcion,
            "dispositivo_id": row.dispositivo_id,
            "dispositivo_nombre": row.dispositivo_nombre,
            "servidor_id": row.servidor_id,
            "servidor_nombre": row.servidor_nombre,
            "sesion_inicio": _to_venezuela_time(sesion_inicio).isoformat() if sesion_inicio else None,
            "sesion_fin": _to_venezuela_time(sesion_fin).isoformat() if sesion_fin else None,
            "duracion_segundos": row.duracion_segundos,
            "usuario": row.usuario,
            "origen": row.origen,
        })
    
    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
    }
