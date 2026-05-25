from datetime import datetime, timedelta
from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_usuarios
from app.dependencies import get_current_cliente, get_current_admin
from app.models.dispositivo import Dispositivo
from app.models.dispositivo_sesion import DispositivoSesion
from app.models.servidor_secundario import ServidorSecundario
from app.services.notificacion_service import registrar_accion
from app.services.server_service import HEARTBEAT_OFFLINE_MINUTES, _utcnow, _obtener_dispositivos_de_servidor, _obtener_conteo_videos_servidor
import asyncio

router = APIRouter(tags=["monitoreo"])
logger = logging.getLogger("uvicorn.error")


class ServerRenameBody(BaseModel):
    nombre: str


@router.get("/status")
async def status(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    lista = []
    usuario_id = current_user.get("user_id") if current_user else None
    espacio_critico_umbral = 0.95

    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
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


@router.get("/status-detalle")
async def status_detalle(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    dispositivos_result = await db.execute(select(Dispositivo))
    dispositivos_db = list(dispositivos_result.scalars().all())
    dispositivo_por_codigo: dict[str, Dispositivo] = {
        d.codigo_kiosko: d for d in dispositivos_db
    }

    lista = []
    for s in servidores:
        online = s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
        total = s.almacenamiento_total or 0
        usado = s.almacenamiento_usado or 0
        porcentaje_uso = (usado / total * 100) if total > 0 else 0.0

        dispositivos_runtime = await _obtener_dispositivos_de_servidor(s.ip) if online else []
        runtime_por_codigo = {d["device_id"]: d for d in dispositivos_runtime}

        if online:
            vistos = set(runtime_por_codigo.keys())

            for codigo, info in runtime_por_codigo.items():
                dispositivo = dispositivo_por_codigo.get(codigo)
                if dispositivo is None:
                    dispositivo = Dispositivo(
                        codigo_kiosko=codigo,
                        online=bool(info.get("online", False)),
                        servidor_id=s.id,
                    )
                    db.add(dispositivo)
                    dispositivo_por_codigo[codigo] = dispositivo

                    if bool(info.get("online", False)):
                        sesion = DispositivoSesion(
                            dispositivo_id=codigo,
                            inicio=now,
                        )
                        db.add(sesion)
                        await db.flush()
                else:
                    estaba_online = dispositivo.online
                    ahora_online = bool(info.get("online", False))

                    if not estaba_online and ahora_online:
                        sesion = DispositivoSesion(
                            dispositivo_id=codigo,
                            inicio=now,
                        )
                        db.add(sesion)
                        await db.flush()
                    elif estaba_online and not ahora_online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == codigo,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()

                    dispositivo.online = ahora_online
                    dispositivo.servidor_id = s.id

            for dispositivo in dispositivo_por_codigo.values():
                if dispositivo.servidor_id == s.id and dispositivo.codigo_kiosko not in vistos:
                    if dispositivo.online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()
                    dispositivo.online = False
        else:
            for dispositivo in dispositivo_por_codigo.values():
                if dispositivo.servidor_id == s.id:
                    if dispositivo.online:
                        stmt_sesion = select(DispositivoSesion).where(
                            DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                            DispositivoSesion.fin == None
                        )
                        result_sesion = await db.execute(stmt_sesion)
                        sesion_activa = result_sesion.scalars().first()
                        if sesion_activa:
                            sesion_activa.fin = now
                            duracion = int((now - sesion_activa.inicio).total_seconds())
                            sesion_activa.duracion_segundos = duracion
                            await db.flush()
                    dispositivo.online = False

        dispositivos: list[dict[str, Any]] = []
        for dispositivo in dispositivo_por_codigo.values():
            if dispositivo.servidor_id != s.id:
                continue

            runtime_info = runtime_por_codigo.get(dispositivo.codigo_kiosko, {})
            is_online = bool(dispositivo.online) and online
            nombre_amigable = dispositivo.nombre_amigable
            nombre_mostrado = nombre_amigable if nombre_amigable else dispositivo.codigo_kiosko

            stmt_sesion_activa = select(DispositivoSesion).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.fin == None
            )
            result_sesion_activa = await db.execute(stmt_sesion_activa)
            sesion_activa = result_sesion_activa.scalars().first()

            sesion_activa_bool = sesion_activa is not None

            tiempo_actual = None
            if sesion_activa:
                tiempo_actual = int((now - sesion_activa.inicio).total_seconds())

            stmt_ultima = select(DispositivoSesion).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.duracion_segundos != None
            ).order_by(DispositivoSesion.inicio.desc()).limit(1)
            result_ultima = await db.execute(stmt_ultima)
            ultima_sesion = result_ultima.scalars().first()
            ultima_duracion = ultima_sesion.duracion_segundos if ultima_sesion else None

            stmt_total = select(func.sum(DispositivoSesion.duracion_segundos)).where(
                DispositivoSesion.dispositivo_id == dispositivo.codigo_kiosko,
                DispositivoSesion.duracion_segundos != None
            )
            result_total = await db.execute(stmt_total)
            tiempo_acumulado = result_total.scalar() or 0

            dispositivos.append(
                {
                    "device_id": dispositivo.codigo_kiosko,
                    "nombre_amigable": nombre_amigable,
                    "nombre_mostrado": nombre_mostrado,
                    "online": is_online,
                    "last_seen": runtime_info.get("last_seen"),
                    "sesion_activa": sesion_activa_bool,
                    "tiempo_actual": tiempo_actual,
                    "ultima_duracion": ultima_duracion,
                    "tiempo_acumulado": tiempo_acumulado,
                    "server_id": runtime_info.get("server_id"),
                    "tipo": getattr(dispositivo, 'tipo', 'verificador'),
                    "hora_reinicio": getattr(dispositivo, 'hora_reinicio', None),
                    "reinicio_recurrente": getattr(dispositivo, 'reinicio_recurrente', False),
                }
            )

        dispositivos.sort(key=lambda d: (d["nombre_mostrado"] or "").lower())
        dispositivos_online = sum(1 for d in dispositivos if d.get("online"))

        lista.append(
            {
                "id": s.id,
                "nombre": s.nombre,
                "ip": s.ip,
                "almacenamiento_total": total,
                "almacenamiento_usado": usado,
                "ultimo_heartbeat": s.ultimo_heartbeat.isoformat() if s.ultimo_heartbeat else None,
                "online": online,
                "porcentaje_uso": round(porcentaje_uso, 2),
                "dispositivos_total": len(dispositivos),
                "dispositivos_online": dispositivos_online,
                "dispositivos": dispositivos,
            }
        )

    await db.commit()
    logger.info("status-detalle: respuesta generada para %s servidores", len(lista))

    return {"success": True, "servidores": lista}


@router.patch("/servidores/{server_id}/nombre")
async def renombrar_servidor(
    server_id: int,
    body: ServerRenameBody,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    nuevo_nombre = (body.nombre or "").strip()
    if not nuevo_nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")

    stmt_exists = select(ServidorSecundario).where(
        func.lower(ServidorSecundario.nombre) == nuevo_nombre.lower(),
        ServidorSecundario.id != server_id,
    )
    result_exists = await db.execute(stmt_exists)
    existing = result_exists.scalars().first()
    result_exists.close()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un servidor con ese nombre")

    stmt = select(ServidorSecundario).where(ServidorSecundario.id == server_id)
    result = await db.execute(stmt)
    servidor = result.scalars().first()
    result.close()

    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    servidor.nombre = nuevo_nombre
    await db.commit()

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "RENOMBRAR_SERVIDOR",
                f"Servidor {servidor.ip} renombrado a '{servidor.nombre}'",
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de rename para servidor %s: %s", servidor.id, e)

    return {
        "success": True,
        "server_id": servidor.id,
        "nombre": servidor.nombre,
        "ip": servidor.ip,
    }


@router.delete("/servidores/{server_id}")
async def eliminar_servidor(
    server_id: int,
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_admin),
):
    stmt = select(ServidorSecundario).where(ServidorSecundario.id == server_id)
    result = await db.execute(stmt)
    servidor = result.scalars().first()
    result.close()

    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    nombre_para_log = servidor.nombre
    ip_para_log = servidor.ip

    from app.models.asignacion import PublicidadAsignacion
    from sqlalchemy import delete as sql_delete

    stmt_asig = sql_delete(PublicidadAsignacion).where(
        PublicidadAsignacion.servidor_id == server_id
    )
    await db.execute(stmt_asig)

    stmt_disp = Dispositivo.__table__.update().where(
        Dispositivo.servidor_id == server_id
    ).values(servidor_id=None)
    await db.execute(stmt_disp)

    await db.delete(servidor)
    await db.commit()

    user_id = current_user.get("user_id") if current_user else None
    if user_id is not None:
        try:
            await registrar_accion(
                db,
                user_id,
                "ELIMINAR_SERVIDOR",
                f"Servidor '{nombre_para_log}' ({ip_para_log}) eliminado",
            )
        except Exception as e:
            logger.warning("No se pudo registrar auditoría de eliminación de servidor %s: %s", server_id, e)

    return {"success": True, "message": f"Servidor {server_id} eliminado correctamente"}


@router.get("/monitoreo/servidores/videos-actuales")
async def servidores_videos_actuales(
    db: AsyncSession = Depends(get_db_usuarios),
    current_user: dict = Depends(get_current_cliente),
):
    now = _utcnow()
    umbral = now - timedelta(minutes=HEARTBEAT_OFFLINE_MINUTES)

    stmt = select(ServidorSecundario).order_by(ServidorSecundario.nombre)
    result = await db.execute(stmt)
    servidores = result.scalars().all()

    online_servers = [
        s for s in servidores
        if s.ultimo_heartbeat is not None and s.ultimo_heartbeat >= umbral
    ]

    conteos = await asyncio.gather(*[_obtener_conteo_videos_servidor(s.ip) for s in online_servers])

    data = []
    for server, count in zip(online_servers, conteos):
        data.append(
            {
                "id": server.id,
                "nombre": server.nombre,
                "ip": server.ip,
                "videos_actuales": int(count),
            }
        )

    return {
        "success": True,
        "servidores": data,
    }


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
