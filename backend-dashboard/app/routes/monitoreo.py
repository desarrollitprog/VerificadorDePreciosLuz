from app.dependencies import get_current_admin

"""
Rutas de monitoreo: heartbeat de servidores secundarios y estado.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_usuarios
from app.dependencies import get_current_cliente, validar_api_key
from app.models.servidor_secundario import ServidorSecundario
from app.services.notificacion_service import registrar_accion

router = APIRouter(tags=["monitoreo"])


class HeartbeatBody(BaseModel):
    nombre_servidor: str
    ip: str
    almacenamiento_total: int
    almacenamiento_usado: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    stmt = select(ServidorSecundario).where(ServidorSecundario.nombre == body.nombre_servidor)
    result = await db.execute(stmt)
    servidor = result.scalars().first()

    if servidor:
        servidor.ip = body.ip
        servidor.almacenamiento_total = body.almacenamiento_total
        servidor.almacenamiento_usado = body.almacenamiento_usado
        servidor.ultimo_heartbeat = now
    else:
        servidor = ServidorSecundario(
            nombre=body.nombre_servidor,
            ip=body.ip,
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


# Umbral: sin heartbeat en los últimos 8 minutos = offline
HEARTBEAT_OFFLINE_MINUTES = 8


@router.get("/status")
async def status(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    """
    Devuelve la lista de todos los servidores.
    Marca como offline los que no han enviado heartbeat en los últimos 5 minutos.
    Requiere autenticación (Cliente o Admin).
    Además, registra en auditoría los cambios de estado y genera alertas automáticas.
    """
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    lista = []
    usuario_id = current_user.get("id") if current_user else None
    espacio_critico_umbral = 0.95  # 95% de uso

    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
        # Auditoría: registrar cambio de estado
        estado_actual = "ONLINE" if online else "OFFLINE"
        estado_prev = getattr(s, "_last_estado", None)
        if estado_prev is not None and estado_actual != estado_prev:
            await registrar_accion(
                db,
                usuario_id,
                tipo="CAMBIO_ESTADO_SERVIDOR",
                descripcion=f"Servidor '{s.nombre}' cambió a {estado_actual}"
            )
        s._last_estado = estado_actual

        # Alerta automática: espacio crítico
        espacio_usado = s.almacenamiento_usado / s.almacenamiento_total if s.almacenamiento_total else 0
        if online and espacio_usado >= espacio_critico_umbral:
            await registrar_accion(
                db,
                usuario_id,
                tipo="ALERTA_SERVIDOR",
                descripcion=f"Servidor '{s.nombre}' espacio crítico: {espacio_usado*100:.1f}%"
            )

        total = s.almacenamiento_total or 0
        usado = s.almacenamiento_usado or 0
        porcentaje_uso = (usado / total * 100) if total > 0 else 0.0

        lista.append({
            "id": s.id,
            "nombre": s.nombre,
            "ip": s.ip,
            "almacenamiento_total": s.almacenamiento_total,
            "almacenamiento_usado": s.almacenamiento_usado,
            "ultimo_heartbeat": s.ultimo_heartbeat.isoformat() if s.ultimo_heartbeat else None,
            "online": online,
            "porcentaje_uso": round(porcentaje_uso, 2),
        })

    return {"success": True, "servidores": lista}

@router.get("/alertas")
async def obtener_alertas(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(ServidorSecundario)
    result = await db.execute(stmt)
    servidores = result.scalars().all()
    alertas = []
    for s in servidores:
        if s.almacenamiento_total and s.almacenamiento_usado:
            porcentaje = (s.almacenamiento_usado / s.almacenamiento_total) * 100
            if porcentaje > 90:
                alertas.append({
                    "nombre_servidor": s.nombre,
                    "mensaje": f"Advertencia: el servidor '{s.nombre}' está al {porcentaje:.1f}% de capacidad."
                })
    return alertas