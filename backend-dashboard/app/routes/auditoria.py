from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _to_venezuela_time(dt: datetime) -> datetime:
    """Convierte datetime UTC a timezone de Venezuela (UTC-4)"""
    if dt is None:
        return None
    return dt - timedelta(hours=4)
from typing import Any, Optional
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente
from app.models.notificacion import Notificacion
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.dispositivo import Dispositivo
from app.models.servidor_secundario import ServidorSecundario

router = APIRouter(tags=["auditoria"])
logger = logging.getLogger("uvicorn.error")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


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


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "0s"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


@router.get("/auditoria")
async def obtener_auditoria(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
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
    """
    offset = (page - 1) * limit
    now = _utcnow()
    
    items: list[dict[str, Any]] = []
    
    # ===============================
    # 1. CONSULTAR SESIONES DE DISPOSITIVOS
    # ===============================
    sesion_stmt = select(
        DispositivoSesion,
        Dispositivo.codigo_kiosko,
        Dispositivo.nombre_amigable,
        ServidorSecundario.id.label("srv_id"),
        ServidorSecundario.nombre.label("srv_nombre"),
    ).select_from(
        DispositivoSesion
    ).outerjoin(
        Dispositivo, Dispositivo.codigo_kiosko == DispositivoSesion.dispositivo_id
    ).outerjoin(
        ServidorSecundario, ServidorSecundario.id == Dispositivo.servidor_id
    )
    
    sesion_conditions = []
    if dispositivo_id:
        sesion_conditions.append(DispositivoSesion.dispositivo_id == dispositivo_id)
    if servidor_id:
        sesion_conditions.append(ServidorSecundario.id == servidor_id)
    if fecha_desde:
        sesion_conditions.append(DispositivoSesion.inicio >= fecha_desde)
    if fecha_hasta:
        sesion_conditions.append(DispositivoSesion.inicio <= fecha_hasta)
    
    if sesion_conditions:
        sesion_stmt = sesion_stmt.where(*sesion_conditions)
    
    sesion_stmt = sesion_stmt.order_by(DispositivoSesion.inicio.desc())
    
    result_sesiones = await db.execute(sesion_stmt)
    rows_sesiones = result_sesiones.all()
    
    for row in rows_sesiones:
        sesion = row[0]
        disp_codigo = row[1]
        disp_nombre = row[2]
        srv_id = row[3]
        srv_nombre = row[4]
        
        tipo_evento = "SESION_ACTIVA" if sesion.fin is None else "SESION_CERRADA"
        
        # Determinar el tipo correcto basado en la descripción
        if sesion.fin is None:
            descripcion = f"Dispositivo '{disp_nombre or disp_codigo}' ({disp_codigo}) conectado al servidor '{srv_nombre or 'Desconocido'}'"
            tipo_evento = "CONEXION_DISPOSITIVO"
        else:
            duracion_formatted = _format_duration(sesion.duracion_segundos)
            descripcion = f"Dispositivo '{disp_nombre or disp_codigo}' ({disp_codigo}) desconectado del servidor '{srv_nombre or 'Desconocido'}'. Duración: {duracion_formatted}"
            tipo_evento = "DESCONEXION_DISPOSITIVO"
        
        items.append({
            "id": sesion.id,
            "fecha": _to_venezuela_time(sesion.inicio).isoformat() if sesion.inicio else None,
            "tipo": tipo_evento,
            "descripcion": descripcion,
            "dispositivo_id": disp_codigo,
            "dispositivo_nombre": disp_nombre,
            "servidor_id": srv_id,
            "servidor_nombre": srv_nombre,
            "sesion_inicio": _to_venezuela_time(sesion.inicio).isoformat() if sesion.inicio else None,
            "sesion_fin": _to_venezuela_time(sesion.fin).isoformat() if sesion.fin else None,
            "duracion_segundos": sesion.duracion_segundos,
            "usuario": None,
            "origen": "sesion",
        })
    
    # ===============================
    # 2. CONSULTAR NOTIFICACIONES
    # ===============================
    notif_stmt = select(Notificacion).order_by(Notificacion.fecha_creacion.desc())
    
    notif_conditions = []
    if tipo:
        notif_conditions.append(Notificacion.tipo == tipo)
    if fecha_desde:
        notif_conditions.append(Notificacion.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        notif_conditions.append(Notificacion.fecha_creacion <= fecha_hasta)
    
    if notif_conditions:
        notif_stmt = notif_stmt.where(*notif_conditions)
    
    result_notif = await db.execute(notif_stmt)
    rows_notif = result_notif.scalars().all()
    
    for notif in rows_notif:
        # Usar campos directas de la notificación si existen
        dispositivo_id = notif.dispositivo_id
        servidor_id = notif.servidor_id
        dispositivo_nombre = None
        servidor_nombre = None
        
        # Si no tiene dispositivo_id, intentar extraer de la descripción
        if not dispositivo_id:
            desc = notif.descripcion or ""
            import re
            
            # Extraer dispositivo de descripciones tipo "Dispositivo 'nombre' (id)"
            match_disp = re.search(r"Dispositivo\s+['\"]([^'\"]+)['\"]\s+\(([^)]+)\)", desc)
            if match_disp:
                dispositivo_nombre = match_disp.group(1)
                dispositivo_id = match_disp.group(2)
            
            # Extraer servidor de descripciones tipo "servidor 'nombre' (ip)"
            match_srv = re.search(r"servidor\s+['\"]([^'\"]+)['\"]\s+\(([^)]+)\)", desc, re.IGNORECASE)
            if match_srv:
                servidor_nombre = match_srv.group(1)
        else:
            # Obtener nombres de dispositivo y servidor desde la BD
            if dispositivo_id:
                stmt_disp = select(Dispositivo).where(Dispositivo.codigo_kiosko == dispositivo_id)
                result_disp = await db.execute(stmt_disp)
                disp = result_disp.scalars().first()
                if disp:
                    dispositivo_nombre = disp.nombre_amigable
            
            if servidor_id:
                stmt_srv = select(ServidorSecundario).where(ServidorSecundario.id == servidor_id)
                result_srv = await db.execute(stmt_srv)
                srv = result_srv.scalars().first()
                if srv:
                    servidor_nombre = srv.nombre
        
        desc = notif.descripcion or ""
        
        items.append({
            "id": notif.id,
            "fecha": _to_venezuela_time(notif.fecha_creacion).isoformat() if notif.fecha_creacion else None,
            "tipo": notif.tipo,
            "descripcion": desc,
            "dispositivo_id": dispositivo_id,
            "dispositivo_nombre": dispositivo_nombre,
            "servidor_id": servidor_id,
            "servidor_nombre": servidor_nombre,
            "sesion_inicio": None,
            "sesion_fin": None,
            "duracion_segundos": None,
            "usuario": str(notif.usuario_id) if notif.usuario_id else None,
            "origen": "notificacion",
        })
    
    # ===============================
    # 3. APLICAR FILTROS ADICIONALES
    # ===============================
    if busqueda:
        busqueda_lower = busqueda.lower()
        items = [
            item for item in items
            if (item.get("descripcion") and busqueda_lower in item["descripcion"].lower())
            or (item.get("dispositivo_id") and busqueda_lower in item["dispositivo_id"].lower())
            or (item.get("dispositivo_nombre") and busqueda_lower in item["dispositivo_nombre"].lower())
            or (item.get("servidor_nombre") and busqueda_lower in item["servidor_nombre"].lower())
            or (item.get("tipo") and busqueda_lower in item["tipo"].lower())
        ]
    
    # Filtrar por dispositivo_id si se pasó como filtro específico (después de la búsqueda)
    if dispositivo_id:
        items = [item for item in items if item.get("dispositivo_id") == dispositivo_id]
    
    # Filtrar por servidor_id si se pasó como filtro específico
    if servidor_id:
        items = [item for item in items if item.get("servidor_id") == servidor_id]
    
    # ===============================
    # 4. ORDENAR Y PAGINAR
    # ===============================
    items.sort(key=lambda x: x.get("fecha") or "", reverse=True)
    
    total = len(items)
    paginated_items = items[offset:offset + limit]
    
    return {
        "success": True,
        "items": paginated_items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
    }
