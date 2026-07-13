from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import validar_api_key
from app.models.dispositivo import Dispositivo
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.servidor_secundario import ServidorSecundario

router = APIRouter(tags=["monitoreo"])


class HeartbeatBody(BaseModel):
    nombre_servidor: str
    ip: str
    almacenamiento_total: int
    almacenamiento_usado: int


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatBody,
    db: AsyncSession = Depends(get_db_usuarios),
    _: bool = Depends(validar_api_key),
):
    """
    Llamado por los servidores secundarios.
    Crea el servidor si no existe; si existe, actualiza IP, almacenamiento y ultimo_heartbeat.
    """
    now = _utcnow()
    nombre_servidor = (body.nombre_servidor or "").strip()
    ip_servidor = (body.ip or "").strip()

    # 1) Prioridad por IP (más estable que hostname en despliegues con contenedores)
    stmt_ip = select(ServidorSecundario).where(ServidorSecundario.ip == ip_servidor).order_by(ServidorSecundario.id.asc())
    result_ip = await db.execute(stmt_ip)
    servidor = result_ip.scalars().first()

    # 2) Fallback por nombre (compatibilidad hacia atrás)
    if servidor is None:
        stmt_nombre = select(ServidorSecundario).where(ServidorSecundario.nombre == nombre_servidor).order_by(ServidorSecundario.id.asc())
        result_nombre = await db.execute(stmt_nombre)
        servidor = result_nombre.scalars().first()

    if servidor:
        if not (servidor.nombre or "").strip():
            servidor.nombre = nombre_servidor
        servidor.ip = ip_servidor
        servidor.almacenamiento_total = body.almacenamiento_total
        servidor.almacenamiento_usado = body.almacenamiento_usado
        servidor.ultimo_heartbeat = now
    else:
        servidor = ServidorSecundario(
            nombre=nombre_servidor,
            ip=ip_servidor,
            almacenamiento_total=body.almacenamiento_total,
            almacenamiento_usado=body.almacenamiento_usado,
            ultimo_heartbeat=now,
        )
        db.add(servidor)

    await db.commit()
    await db.refresh(servidor)
    return {
        "success": True,
        "message": "Heartbeat registrado.",
        "servidor_id": servidor.id,
    }


@router.post("/dispositivo-offline/{device_id}")
async def dispositivo_offline(
    device_id: str,
    db: AsyncSession = Depends(get_db_usuarios),
    _: bool = Depends(validar_api_key),
):
    """
    Notificado por backend-api cuando un dispositivo se desconecta del WebSocket.
    Cierra la sesión activa y marca el dispositivo como offline.
    Idempotente: si no hay sesión activa o el dispositivo no existe, retorna 200.
    """
    now = _utcnow()

    stmt = select(Dispositivo).where(Dispositivo.codigo_kiosko == device_id)
    result = await db.execute(stmt)
    dispositivo = result.scalars().first()

    if dispositivo is None:
        return {"success": True, "message": "Dispositivo no encontrado, ignorado."}

    if not dispositivo.online:
        return {"success": True, "message": "Dispositivo ya estaba offline."}

    stmt_sesion = select(DispositivoSesion).where(
        DispositivoSesion.dispositivo_id == device_id,
        DispositivoSesion.fin == None,
    ).order_by(DispositivoSesion.inicio.desc())
    result_sesion = await db.execute(stmt_sesion)
    sesiones_activas = result_sesion.scalars().all()

    cerradas = 0
    for sesion in sesiones_activas:
        sesion.fin = now
        sesion.duracion_segundos = int((now - sesion.inicio).total_seconds())
        cerradas += 1

    dispositivo.online = False

    await db.commit()
    return {
        "success": True,
        "message": f"Dispositivo {device_id} marcado offline.",
        "sesiones_cerradas": cerradas,
    }
